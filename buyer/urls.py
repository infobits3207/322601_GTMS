from django.urls import path
from buyer import views, add_buyer_and_related_cmp_view

app_name = 'buyer'

urlpatterns = [
    path('buyer_list/', views.buyer_list, name='buyer_list'),
    
    path('add_buyer/', add_buyer_and_related_cmp_view.add_buyer, name='add_buyer'),
]