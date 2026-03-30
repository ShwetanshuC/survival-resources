from django.urls import path
from . import views

urlpatterns = [
    path('api/food/', views.search_food, name='search_food'),
    path('api/food/events/', views.search_food_events, name='search_food_events'),
]
