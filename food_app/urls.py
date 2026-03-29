from django.urls import path
from . import views

urlpatterns = [
    path('api/food/', views.search_food, name='search_food'),
]
