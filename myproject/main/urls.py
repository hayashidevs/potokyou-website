from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='main'),
    path('license/', views.license_agreement, name='license_agreement'),
    path('download/linux/', views.download_linux, name='download_linux'),
    path('download/windows/', views.download_windows, name='download_windows'),
    path('download/macos/', views.download_macos, name='download_macos'),
]
