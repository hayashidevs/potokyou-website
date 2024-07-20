from django.shortcuts import render, redirect
from django.http import HttpResponse

def index(request):
    language = request.COOKIES.get('django_language', 'en')
    if language == 'ru':
        template = 'main/index_ru.html'
    else:
        template = 'main/index_en.html'
    return render(request, template)

def license_agreement(request):
    language = request.COOKIES.get('django_language', 'en')
    if language == 'ru':
        template = 'main/license_ru.html'
    else:
        template = 'main/license_en.html'
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
    response = redirect('/')
    response.set_cookie('django_language', language)
    return response
