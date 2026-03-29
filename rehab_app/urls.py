from django.urls import path
from . import views

urlpatterns = [
    path('api/rehab/', views.search_rehab, name='search_rehab'),
]
