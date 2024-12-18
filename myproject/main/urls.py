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
    path('create-payment/<uuid:client_id>/<uuid:rate_id>/', views.create_payment, name='create_payment'),
    path('thanks/', views.thanks_view, name='thanks_view'),
    path('download-config/<str:config_filename>/<str:hash_digest>/', views.download_config, name='download_config'),
    path('telegram/create-payment/<str:client_id>/<str:rate_id>/', views.telegram_create_payment, name='telegram_create_payment'),
    path('telegram/thanks/', views.telegram_thanks_view, name='telegram_thanks'),
    path('telegram/download-config/<str:config_filename>/<str:hash_digest>/', views.telegram_download_config, name='telegram_download_config'),
    path('yookassa_webhook/', views.yookassawebhook, name='yookassawebhook'),  # Add the webhook endpoint
]
