from django.urls import path
from . import views

urlpatterns = [
    path('api/shelter/', views.search_shelter, name='search_shelter'),
]
