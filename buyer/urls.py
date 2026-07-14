from django.urls import path
from buyer import views, add_buyer_and_related_cmp_view, email_view

app_name = 'buyer'

urlpatterns = [
    path('buyer_list/', views.buyer_list, name='buyer_list'),
    
    path('add_buyer/', add_buyer_and_related_cmp_view.add_buyer, name='add_buyer'),

    path('send_bulk_email/', email_view.send_bulk_email, name='send_bulk_email')
]