from django.urls import path
from supplier import add_supllier_and_related_companies_view, views, email_view, edit_supplier_view

app_name = 'supplier'

urlpatterns = [
    path('suppliers_list/', views.suppliers_list,name='suppliers_list'),
    path('delete_supplier/', views.delete_supplier, name='delete_supplier'),

    path('add_supplier/', add_supllier_and_related_companies_view.supplier_add, name='supplier_add'),
    path('fetch_products/', add_supllier_and_related_companies_view.fetch_products, name='fetch_products'),
    path('related_companies/<int:sp_id>', add_supllier_and_related_companies_view.related_companies, name='related_companies'),

    path('send-email/', email_view.send_company_email, name='send_company_email'),
    path('<int:sp_id>/email_history/', email_view.email_history, name='email_history'),
    path('send-bulk-email/', email_view.send_bulk_email, name='send_bulk_email'),

    path('supplier_detail/<int:sp_id>', edit_supplier_view.supplier_detail, name='supplier_detail'),
    path('edit_supplier/<int:sp_id>', edit_supplier_view.edit_supplier, name='edit_supplier'),
]