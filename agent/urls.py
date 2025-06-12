"""
URL configuration for agent project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from patient import views
urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.home, name='home'),
    path('login/', views.login_view, name='login'),
    path('home/', views.hospital_home, name='hospital_home'),
    path('about-us/', views.about_us, name='about-us'),
    path('logout/', views.logout, name='logout'),
    path('reset-password/', views.reset_password, name='reset-password'),
    path('patient-register/', views.patient_register, name='patient-register'),
    path('chatbot/', views.chatbot, name='chatbot'),
    path('camera_feed/', views.camera_feed, name='camera_feed'),
    path('api/chat/', views.chat_api, name='chat_api'),
    path('release_camera', views.release_camera, name='release_camera'),
    path('get_danger_status/', views.get_danger_status, name='get_danger_status'),
    #path('reset-password/', views.reset_password, name='reset-password'),

]
