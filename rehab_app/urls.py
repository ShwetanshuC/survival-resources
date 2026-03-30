from django.urls import path
from . import views

urlpatterns = [
    path('api/rehab/', views.search_rehab, name='search_rehab'),
    path('api/rehab/events/', views.search_rehab_events, name='search_rehab_events'),
]
