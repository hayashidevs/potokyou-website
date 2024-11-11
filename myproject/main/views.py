from django.shortcuts import render, redirect
from django.http import HttpResponse, Http404, FileResponse, JsonResponse
import os
import json
import requests
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from .config import DJANGO_API_URL, WGAPI_URL
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.conf import settings

from yookassa import Configuration, Payment

import hmac
import hashlib
from datetime import datetime, timedelta
import uuid

Configuration.account_id = settings.YOOKASSA_SHOP_ID
Configuration.secret_key = settings.YOOKASSA_SECRET_KEY


def get_template(language, en_template, ru_template):
    return ru_template if language == 'ru' else en_template

def detect_language(request):
    language = request.COOKIES.get('django_language')
    if not language:
        user_lang = request.META.get('HTTP_ACCEPT_LANGUAGE', '')
        if user_lang.startswith('ru'):
            language = 'ru'
        else:
            language = 'en'
    return language

def index(request):
    language = detect_language(request)
    template = get_template(language, 'main/index_en.html', 'main/index_ru.html')
    return render(request, template)

def license_agreement(request):
    language = detect_language(request)
    template = get_template(language, 'main/license_en.html', 'main/license_ru.html')
    return render(request, template)

def mobile_app_policy(request):
    language = detect_language(request)
    template = get_template(language, 'main/mobile_app_policy_en.html', 'main/mobile_app_policy_ru.html')
    return render(request, template)

def download_linux(request):
    response = HttpResponse()
    response['Content-Disposition'] = 'attachment; filename=linux_installer.sh'
    response.write("Content of the Linux installer script.")
    return response

def download_windows(request):
    response = HttpResponse()
    response['Content-Disposition'] = 'attachment; filename=windows_installer.exe'
    response.write("Content of the Windows installer executable.")
    return response

def download_macos(request):
    response = HttpResponse()
    response['Content-Disposition'] = 'attachment; filename=macos_installer.dmg'
    response.write("Content of the MacOS installer disk image.")
    return response

def change_language(request, language):
    response = redirect(request.META.get('HTTP_REFERER', '/'))
    response.set_cookie('django_language', language)
    return response


def process_subscription(client_id, rate_id, request):
    subscription_url = f"{DJANGO_API_URL}/api/subscriptions/"
    datestart = datetime.now()

    # Fetch rate data to determine subscription duration
    rate_data_response = requests.get(f"{DJANGO_API_URL}/api/rates/{rate_id}/")
    if rate_data_response.status_code == 200:
        rate_data = rate_data_response.json()
        day_amount = rate_data.get("dayamount", 0)
        dateend = datestart + timedelta(days=day_amount)
    else:
        print("Error fetching rate data:", rate_data_response.status_code)
        return None

    # Prepare data for creating the subscription
    subscription_data = {
        "clientid": client_id,
        "rateid": rate_id,
        "datestart": datestart.isoformat(),
        "dateend": dateend.isoformat(),
        "name": "Subscription name",  # Optional name field
        "is_used": False,
    }

    # Attempt to create the subscription
    response = requests.post(subscription_url, json=subscription_data)
    if response.status_code == 201:
        subscription_id = response.json().get("id")
        request.session['subscription_id'] = subscription_id  # Save to session
        request.session.save()  # Ensure session is saved

        print(f"Subscription created with ID: {subscription_id}")
        return subscription_id
    else:
        print("Error creating subscription:", response.status_code, response.json())
        return None
    
@api_view(['POST'])
def update_subscription_dateend(request):
    subscription_id = request.data.get('subscription_id')
    dateend_update = request.data.get('dateend')

    # API URL for updating the subscription
    update_subscription_url = f"{DJANGO_API_URL}/api/update_subscription_dateend/"

    # Payload for the update request
    payload = {
        "subscription_id": subscription_id,
        "dateend": dateend_update
    }

    # Make the API call to update the subscription dateend
    response = requests.post(update_subscription_url, json=payload)
    
    # Process response
    if response.status_code == 200:
        return Response({'status': 'success', 'message': 'Subscription dateend updated successfully'})
    else:
        return Response({'status': 'error', 'message': 'Failed to update subscription dateend'}, status=response.status_code)
    
def download_config(request, config_filename, hash_digest):
    # Verify hash for anti-tampering
    secret_key = settings.SECRET_KEY
    calculated_hash = hmac.new(secret_key.encode(), config_filename.encode(), hashlib.sha256).hexdigest()

    if hash_digest != calculated_hash:
        return HttpResponse("Unauthorized access.", status=403)

    # File path
    config_path = os.path.join(settings.BASE_DIR, "main", "temp_configs", config_filename)

    # Serve the config file if it exists
    if os.path.exists(config_path):
        return FileResponse(open(config_path, 'rb'), as_attachment=True, filename=config_filename)
    else:
        raise Http404("Config file not found.")

    
@csrf_exempt
def thanks_view(request):
    # Retrieve session data
    client_id = request.session.get('client_id')
    rate_id = request.session.get('rate_id')
    payment_id = request.session.get('payment_id')
    subscription_id = request.session.get('subscription_id')

    # Check if all session data is present
    if not all([client_id, rate_id, payment_id, subscription_id]):
        return HttpResponse("Session data is missing. Please restart the payment process.", status=400)

    try:
        # Prepare the request data for the WGAPI to generate the config
        request_data = json.dumps({"subscription_id": subscription_id})
        response = requests.post(f"{WGAPI_URL}/wireguard/add_user/", data=request_data)

        # Log the response from the WGAPI for debugging
        print("WGAPI /add_user/ response:", response.status_code, response.text)

        # Check if WGAPI returned a success response with config content
        if response.status_code == 200 and response.json().get("status") == "success":
            config_content = response.json().get("config_content")
            config_filename = f"{subscription_id}.conf"
            config_path = os.path.join(settings.BASE_DIR, "main", "temp_configs", config_filename)

            # Ensure the temp_configs directory exists
            os.makedirs(os.path.dirname(config_path), exist_ok=True)

            # Save the config content to a file
            with open(config_path, 'w') as config_file:
                config_file.write(config_content)

            # Generate a secure link for downloading the config file
            secret_key = settings.SECRET_KEY
            hash_digest = hmac.new(secret_key.encode(), config_filename.encode(), hashlib.sha256).hexdigest()
            download_link = f"/download-config/{config_filename}/{hash_digest}/"

            context = {
                'download_link': download_link,
            }
            return render(request, 'thanks.html', context)
        else:
            print("Error creating configuration file from WGAPI:", response.status_code, response.json())
            return HttpResponse("Error creating configuration file.", status=400)

    except Exception as e:
        print("Exception during config creation:", str(e))
        return HttpResponse("Internal server error.", status=500)
    
def create_payment(request, client_id, rate_id):
    # Set API URLs for the "framework" project
    framework_client_url = f"{DJANGO_API_URL}/api/clients/"
    framework_rate_url = f"{DJANGO_API_URL}/api/rates/"

    print(f"Fetching client data from: {framework_client_url}{client_id}/")
    print(f"Fetching rate data from: {framework_rate_url}{rate_id}/")

    # Fetch client data
    client_response = requests.get(f"{framework_client_url}{client_id}/")
    if client_response.status_code != 200:
        print("Error fetching client data:", client_response.status_code, client_response.json())
        return HttpResponse("Error fetching client data from framework project.", status=400)
    client_obj = client_response.json()
    print("Fetched client data:", client_obj)

    # Fetch rate data
    rate_response = requests.get(f"{framework_rate_url}{rate_id}/")
    if rate_response.status_code != 200:
        print("Error fetching rate data:", rate_response.status_code, rate_response.json())
        return HttpResponse("Error fetching rate data from framework project.", status=400)
    rate_obj = rate_response.json()
    print("Fetched rate data:", rate_obj)

    # Create a payment with YooKassa
    try:
        payment = Payment.create({
            "amount": {
                "value": str(rate_obj["price"]),
                "currency": "RUB"
            },
            "confirmation": {
                "type": "redirect",
                "return_url": request.build_absolute_uri('/thanks/')
            },
            "capture": True,
            "description": f"Subscription payment for {rate_obj['name']}"
        })

        confirmation_url = getattr(payment.confirmation, 'confirmation_url', None)
        
        if confirmation_url:
            # Set session data
            request.session['payment_id'] = str(payment.id)
            request.session['client_id'] = str(client_id)
            request.session['rate_id'] = str(rate_id)
            request.session['config_filename'] = 'your_config_filename_here'  # Use actual config filename

            # Confirm session data was set
            print("Session data set:", request.session.items())
            request.session.save()  # Save session data for debugging
            return redirect(confirmation_url)
        else:
            return HttpResponse("Error: confirmation URL missing in payment response.", status=500)

    except Exception as e:
        return HttpResponse("Error creating payment with YooKassa.", status=400)
    

def telegram_create_payment(request, client_id, rate_id):
    # Fetch client and rate data
    client_url = f"{DJANGO_API_URL}/api/clients/{client_id}/"
    rate_url = f"{DJANGO_API_URL}/api/rates/{rate_id}/"

    client_response = requests.get(client_url)
    rate_response = requests.get(rate_url)

    if client_response.status_code != 200 or rate_response.status_code != 200:
        return HttpResponse("Error fetching client or rate data.", status=400)

    client_data = client_response.json()
    rate_data = rate_response.json()

    try:
        payment = Payment.create({
            "amount": {
                "value": str(rate_data["price"]),
                "currency": "RUB"
            },
            "confirmation": {
                "type": "redirect",
                "return_url": request.build_absolute_uri('/telegram/thanks/')
            },
            "capture": True,
            "description": f"Telegram subscription payment for {rate_data['name']}"
        })

        confirmation_url = getattr(payment.confirmation, 'confirmation_url', None)
        if confirmation_url:
            request.session['telegram_payment_id'] = str(payment.id)
            request.session['telegram_client_id'] = client_id
            request.session['telegram_rate_id'] = rate_id
            request.session.save()
            return redirect(confirmation_url)
        else:
            return HttpResponse("Error: confirmation URL missing in payment response.", status=500)

    except Exception as e:
        return HttpResponse("Error creating payment for Telegram.", status=400)
    
@csrf_exempt
def telegram_thanks_view(request):
    client_id = request.session.get('telegram_client_id')
    rate_id = request.session.get('telegram_rate_id')
    payment_id = request.session.get('telegram_payment_id')
    subscription_id = request.session.get('telegram_subscription_id')

    if not all([client_id, rate_id, payment_id, subscription_id]):
        return HttpResponse("Session data is missing. Please restart the payment process.", status=400)

    # Generate config using WGAPI and send to Telegram bot
    request_data = json.dumps({"subscription_id": subscription_id})
    response = requests.post(f"{WGAPI_URL}/wireguard/add_user/", data=request_data)

    if response.status_code == 200 and response.json().get("status") == "success":
        config_content = response.json().get("config_content")
        config_filename = f"{subscription_id}.conf"
        config_path = os.path.join(settings.BASE_DIR, "main", "temp_configs", config_filename)

        with open(config_path, 'w') as config_file:
            config_file.write(config_content)

        secret_key = settings.SECRET_KEY
        hash_digest = hmac.new(secret_key.encode(), config_filename.encode(), hashlib.sha256).hexdigest()

        return render(request, 'thanks.html')
    else:
        return HttpResponse("Error creating configuration file.", status=400)
    
def telegram_download_config(request, config_filename, hash_digest):
    secret_key = settings.SECRET_KEY
    calculated_hash = hmac.new(secret_key.encode(), config_filename.encode(), hashlib.sha256).hexdigest()

    if hash_digest != calculated_hash:
        return HttpResponse("Unauthorized access.", status=403)

    config_path = os.path.join(settings.BASE_DIR, "main", "temp_configs", config_filename)
    if os.path.exists(config_path):
        return FileResponse(open(config_path, 'rb'), as_attachment=True, filename=config_filename)
    else:
        raise Http404("Config file not found.")
    

# Webhook to handle asynchronous payment confirmation
@csrf_exempt
def yookassa_webhook(request):
    if request.method == 'POST':
        data = json.loads(request.body)

        payment_id = data.get("object", {}).get("id")
        payment_status = data.get("object", {}).get("status")

        # Check if payment succeeded
        if payment_status == 'succeeded' and payment_id == request.session.get('telegram_payment_id'):
            client_id = request.session.get('telegram_client_id')
            rate_id = request.session.get('telegram_rate_id')
            subscription_id = process_subscription(client_id, rate_id, request)
            if subscription_id is None:
                return HttpResponse("Error processing subscription.", status=400)
            request.session['telegram_subscription_id'] = str(subscription_id)

            # Generate config using WGAPI
            request_data = json.dumps({"subscription_id": subscription_id})
            response = requests.post(f"{settings.WGAPI_URL}/wireguard/add_user/", data=request_data)

            if response.status_code == 200 and response.json().get("status") == "success":
                config_content = response.json().get("config_content")
                config_filename = f"{subscription_id}.conf"
                config_path = os.path.join(settings.BASE_DIR, "main", "temp_configs", config_filename)

                with open(config_path, 'w') as config_file:
                    config_file.write(config_content)

                # Generate a secure hash for the download link
                secret_key = settings.SECRET_KEY
                hash_digest = hmac.new(secret_key.encode(), config_filename.encode(), hashlib.sha256).hexdigest()

                # Respond indicating the config is ready
                return JsonResponse({
                    'status': 'success',
                    'message': 'Config generated. Return to Telegram to get it.',
                    'download_link': f"/telegram/download-config/{config_filename}/{hash_digest}/"
                })
            else:
                return HttpResponse("Error creating configuration file via webhook.", status=400)

        return JsonResponse({"status": "ignored", "message": "Payment status not succeeded or unmatched payment ID."}, status=400)

    return HttpResponse(status=405)
