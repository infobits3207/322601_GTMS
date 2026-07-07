from django.urls import path
from supplier import views, add_supllier_view, supplier_details_view

app_name = 'supplier'

urlpatterns = [
    path('suppliers_list/', views.suppliers_list,name='suppliers_list'),

    path('add_supplier/', add_supllier_view.supplier_add, name='supplier_add'),
    path('fetch_products/', add_supllier_view.fetch_products, name='fetch_products'),

    path('supplier_detail/<int:sp_id>', supplier_details_view.supplier_detail, name='supplier_detail'),
    path('edit_supplier/<int:sp_id>', supplier_details_view.edit_supplier, name='edit_supplier'),
]