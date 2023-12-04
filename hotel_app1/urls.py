from django.contrib import admin
from django.urls import path, include
from . import views

urlpatterns = [
    path('', views.home, name = "home"),
    path('register', views.register, name = "register"),
    path('log_in', views.log_in, name = "log_in"),
    path('log_out', views.log_out, name = "log_out"),
    path('search/', views.search, name = "search"),
    path('searched_hotels', views.searched_hotels, name='searched_hotels'),
    path('searched_hotels/<int:id>', views.hotel_details, name='hotel_details'),
]
