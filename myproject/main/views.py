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

from django.core.cache import cache

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

    # Fetch client data for meaningful naming
    client_response = requests.get(f"{DJANGO_API_URL}/api/clients/{client_id}/")
    if client_response.status_code == 200:
        client_data = client_response.json()
        client_name = client_data.get("name", f"Client_{client_id}")  # Fallback if name is missing
    else:
        print("Error fetching client data:", client_response.status_code)
        return None

    # Fetch rate data to determine subscription duration and meaningful name
    rate_data_response = requests.get(f"{DJANGO_API_URL}/api/rates/{rate_id}/")
    if rate_data_response.status_code == 200:
        rate_data = rate_data_response.json()
        rate_name = rate_data.get("name", f"Rate_{rate_id}")  # Fallback if name is missing
        day_amount = rate_data.get("dayamount", 0)
        dateend = datestart + timedelta(days=day_amount)
    else:
        print("Error fetching rate data:", rate_data_response.status_code)
        return None

    # Create a meaningful subscription name
    subscription_name = f"{client_name}_Sub_{rate_name}_{datestart.strftime('%Y-%m-%d')}"

    # Prepare data for creating the subscription
    subscription_data = {
        "clientid": client_id,
        "rateid": rate_id,
        "datestart": datestart.isoformat(),
        "dateend": dateend.isoformat(),
        "name": subscription_name,
        "is_used": False,
    }

    # Attempt to create the subscription
    response = requests.post(subscription_url, json=subscription_data)
    if response.status_code == 201:
        subscription_id = response.json().get("id")
        request.session['subscription_id'] = subscription_id  # Save to session
        request.session.save()  # Ensure session is saved

        print(f"Subscription created with ID: {subscription_id} and Name: {subscription_name}")
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
            return render(request, 'thanks_website.html', context)
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
    

@csrf_exempt
def telegram_create_payment(request):
    try:
        # Parse JSON request body
        data = json.loads(request.body)
        client_id = data.get("client_id")
        rate_id = data.get("rate_id")
        type_payment = data.get("type_payment")
        subscription_id = data.get("subscription_id")  # Used for renewal
        ref_client = data.get("ref_client")  # Referral client (optional)

        # Validate required parameters
        if not client_id or not rate_id or not type_payment:
            return HttpResponse("Missing required parameters.", status=400)

        # Fetch client and rate data
        client_url = f"{DJANGO_API_URL}/api/clients/{client_id}/"
        rate_url = f"{DJANGO_API_URL}/api/rates/{rate_id}/"

        client_response = requests.get(client_url)
        rate_response = requests.get(rate_url)

        if client_response.status_code != 200 or rate_response.status_code != 200:
            return HttpResponse("Error fetching client or rate data.", status=400)

        client_data = client_response.json()
        rate_data = rate_response.json()

        # Create payment with YooKassa
        payment_description = f"Telegram subscription payment for {rate_data['name']}"
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
                "description": payment_description
            })

            confirmation_url = getattr(payment.confirmation, 'confirmation_url', None)
            if not confirmation_url:
                return HttpResponse("Error: confirmation URL missing in payment response.", status=500)

            # Store necessary data in cache with a timeout of 10 minutes (600 seconds)
            cache_key = f"payment_{payment.id}"
            if type_payment == "renewal":
                if not subscription_id:
                    return HttpResponse("Missing subscription_id for renewal.", status=400)

                # Store subscription_id for renewal
                cache.set(cache_key, {
                    "client_id": client_id,
                    "rate_id": rate_id,
                    "type_payment": "renewal",
                    "subscription_id": subscription_id
                }, timeout=600)

            elif type_payment == "new_device":
                # Store data for creating a new subscription
                cache_data = {
                    "client_id": client_id,
                    "rate_id": rate_id,
                    "type_payment": "new_device"
                }
                if ref_client:  # Add ref_client if it's provided
                    cache_data["ref_client"] = ref_client

                cache.set(cache_key, cache_data, timeout=600)

            else:
                return HttpResponse("Invalid type_payment value.", status=400)

            return redirect(confirmation_url)

        except Exception as e:
            return HttpResponse(f"Error creating payment for Telegram: {str(e)}", status=400)

    except Exception as e:
        return HttpResponse(f"Error processing request: {str(e)}", status=400)


    
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
    

@csrf_exempt
def yookassawebhook(request):
    if request.method == 'POST':
        try:
            # Parse incoming webhook data
            data = json.loads(request.body)
            print("Received data from YooKassa:", data)  # Debugging

            event_type = data.get("event")
            payment_id = data.get("object", {}).get("id")
            payment_status = data.get("object", {}).get("status")

            # Ensure we are processing only "payment.succeeded" events
            if event_type == 'payment.succeeded' and payment_status == 'succeeded':
                # Retrieve payment data from the cache
                payment_data = cache.get(f"payment_{payment_id}")
                if not payment_data:
                    print("Payment data not found in cache.")  # Debugging
                    return HttpResponse("Payment data not found in cache.", status=400)

                # Extract type_payment, client_id, rate_id, and ref_client from cached data
                type_payment = payment_data.get("type_payment")
                client_id = payment_data.get("client_id")
                rate_id = payment_data.get("rate_id")
                ref_client = payment_data.get("ref_client")  # Optional for new_device

                if type_payment == "renewal":
                    subscription_id = payment_data.get("subscription_id")
                    if not subscription_id:
                        return HttpResponse("Missing subscription_id for renewal.", status=400)

                    # Calculate new end date for the subscription
                    current_date = datetime.now()
                    rate_response = requests.get(f"{DJANGO_API_URL}/api/rates/{rate_id}/")
                    if rate_response.status_code == 200:
                        rate_data = rate_response.json()
                        additional_days = rate_data.get("dayamount", 30)  # Fallback to 30 days if not provided
                        new_dateend = (current_date + timedelta(days=additional_days)).isoformat()

                        # Call update_subscription_dateend view
                        update_payload = {
                            "subscription_id": subscription_id,
                            "dateend": new_dateend
                        }
                        update_response = requests.post(
                            f"{DJANGO_API_URL}/api/update_subscription_dateend/", 
                            json=update_payload
                        )

                        if update_response.status_code == 200:
                            print(f"Subscription {subscription_id} successfully updated with new dateend: {new_dateend}")
                            return HttpResponse("Subscription renewed successfully.", status=200)
                        else:
                            print(f"Failed to update subscription {subscription_id}. Response: {update_response.json()}")
                            return HttpResponse("Error renewing subscription.", status=400)
                    else:
                        return HttpResponse("Error fetching rate data for renewal.", status=400)

                elif type_payment == "new_device":
                    # Proceed with creating a new subscription as before
                    subscription_id = process_subscription(client_id, rate_id, request)
                    if subscription_id is None:
                        print("Error processing subscription.")  # Debugging
                        return HttpResponse("Error processing subscription.", status=400)

                    print(f"Subscription created with ID: {subscription_id}")  # Debugging

                    # Generate secure hash for the download link
                    config_filename = f"{subscription_id}.conf"
                    secret_key = settings.SECRET_KEY
                    hash_digest = hmac.new(secret_key.encode(), config_filename.encode(), hashlib.sha256).hexdigest()
                    download_link = f"/telegram/download-config/{config_filename}/{hash_digest}/"

                    # Prepare payload for external server
                    external_data = {
                        'status': 'success',
                        'message': 'Config generated. Return to Telegram to get it.',
                        'download_link': download_link,
                        'client_id': client_id
                    }

                    # Add ref_client only if it's provided
                    if ref_client:
                        external_data['ref_client'] = ref_client

                    # Send data to external server
                    external_response = requests.post(
                        "http://v2494327.hosted-by-vdsina.ru:9090/payment_completed",
                        json=external_data
                    )

                    if external_response.status_code == 200:
                        print("Data successfully sent to external server")  # Debugging
                        return HttpResponse("Success", status=200)
                    else:
                        print("Failed to send data to external server:", external_response.status_code)
                        return HttpResponse("Error sending data to external server.", status=500)

                else:
                    print("Invalid type_payment value.")  # Debugging
                    return HttpResponse("Invalid type_payment value.", status=400)

            print("Ignored non-succeeded payment or unmatched event type.")  # Debugging
            return JsonResponse({"status": "ignored", "message": "Payment status not succeeded or unmatched payment ID."}, status=400)

        except Exception as e:
            print(f"Error processing webhook: {str(e)}")  # Debugging
            return HttpResponse("Internal server error.", status=500)

    print("Invalid request method")  # Debugging
    return HttpResponse(status=405)
