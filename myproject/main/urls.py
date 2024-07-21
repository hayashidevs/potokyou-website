from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='main'),
    path('privacy/', views.license_agreement, name='license_agreement'),
    path('privacy-mobile-app/', views.mobile_app_policy, name='mobile_app_policy'),
    path('download/linux/', views.download_linux, name='download_linux'),
    path('download/windows/', views.download_windows, name='download_windows'),
    path('download/macos/', views.download_macos, name='download_macos'),
    path('change-language/<str:language>/', views.change_language, name='change_language'),
]
