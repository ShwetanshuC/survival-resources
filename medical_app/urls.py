from django.urls import path
from . import views

urlpatterns = [
    path('api/medical/', views.search_medical, name='search_medical'),
    path('api/medical/events/', views.search_medical_events, name='search_medical_events'),
]
