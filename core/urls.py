from django.urls import path
from core.views import dashboard

urlpatterns = [
    path('',dashboard,name='dashboard'),
]