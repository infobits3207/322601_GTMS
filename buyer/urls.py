from django.urls import path
from buyer import views, add_buyer_and_related_cmp_view, email_view, edit_buyer_view

app_name = 'buyer'

urlpatterns = [
    path('buyer_list/', views.buyer_list, name='buyer_list'),
    
    path('add_buyer/', add_buyer_and_related_cmp_view.add_buyer, name='add_buyer'),
    path('related_sellers/<int:bu_id>', add_buyer_and_related_cmp_view.related_sellers, name='related_sellers'),

    path('send_bulk_email/', email_view.send_bulk_email, name='send_bulk_email'),

    path('buyer_detail/<int:bu_id>', edit_buyer_view.buyer_detail, name='buyer_detail'),
    path('edit_buyer/<int:bu_id>', edit_buyer_view.edit_buyer, name='edit_buyer'),
]