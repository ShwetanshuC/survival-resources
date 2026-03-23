from django.urls import path
from . import views

urlpatterns = [
    # Main home page route
    path('', views.index, name='index'),
    # Generic modular search route allowing varying URL params (e.g ?category=food&lat=x)
    path('api/search_resources/', views.search_resources, name='search_resources'),
]
