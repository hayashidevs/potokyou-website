from django.shortcuts import render, redirect
from django.http import HttpResponse

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
