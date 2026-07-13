from django.urls import path
from enquiry import views, add_enquiry_and_related_seller_view, edit_enquiry_view
# from enquiry import add_enquiry_and_related_companies_view, views, enquiry_details_view, email_view

app_name = 'enquiry'

urlpatterns = [
    path('enquiry_list/', views.enquiry_list,name='enquiry_list'),

    path('add_enquiry/', add_enquiry_and_related_seller_view.add_enquiry, name='add_enquiry'),
    path('related_sellers/<int:en_id>', add_enquiry_and_related_seller_view.related_sellers, name='related_sellers'),
    
    path('edit_enquiry/<int:en_id>', edit_enquiry_view.edit_enquiry, name='edit_enquiry'),
]