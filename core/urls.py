from django.urls import path
from core import views

urlpatterns = [
    path('', views.dashboard,name='dashboard'),
    path('fetch_products/', views.fetch_products, name='fetch_products'),
    path('send-email/', views.send_company_email, name='send_company_email'),
]