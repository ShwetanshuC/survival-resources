from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('sw.js', views.service_worker, name='service_worker'),
]
