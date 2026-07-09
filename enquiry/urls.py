from django.urls import path
from enquiry import add_enquiry_and_related_companies_view, views, enquiry_details_view, email_view

app_name = 'enquiry'

urlpatterns = [
    path('enquiry_list/', views.enquiry_list,name='enquiry_list'),
    path('delete_enquiry/', views.delete_enquiry, name='delete_enquiry'),

    path('add_enquiry/', add_enquiry_and_related_companies_view.enquiry_add, name='enquiry_add'),
    path('fetch_products/', add_enquiry_and_related_companies_view.fetch_products, name='fetch_products'),
    path('related_companies/<int:sp_id>', add_enquiry_and_related_companies_view.related_companies, name='related_companies'),

    path('send-email/', email_view.send_company_email, name='send_company_email'),
    path('<int:sp_id>/email_history/', email_view.email_history, name='email_history'),

    path('enquiry_detail/<int:sp_id>', enquiry_details_view.enquiry_detail, name='enquiry_detail'),
    path('edit_enquiry/<int:sp_id>', enquiry_details_view.edit_enquiry, name='edit_enquiry'),
]