from django.db import models

class supplier_details(models.Model):
    Custom_id = models.CharField(max_length=15,blank=True)
    Company_name = models.CharField(max_length=150,blank=True)
    Description = models.TextField(blank=True)
    Website_link = models.CharField(max_length=100,blank=True)
    GST_number = models.CharField(max_length=20,blank=True)
    IEC_code = models.CharField(max_length=15,blank=True)
    PAN_number = models.CharField(max_length=15,blank=True)
    DIN_number = models.CharField(max_length=25,blank=True)
    CIN_number = models.CharField(max_length=30,blank=True)
    DUNS_number = models.CharField(max_length=30,blank=True)
    Contact_person = models.CharField(max_length=100,blank=True)
    WCPD_code = models.CharField(max_length=10,blank=True)
    Admin_remark = models.TextField(blank=True)
    Created_at = models.DateField(null=True,blank=True)

class supplier_contact_details(models.Model):
    Supplier = models.ForeignKey(supplier_details,on_delete=models.CASCADE,related_name='supplier_contact_details')
    Email = models.EmailField(blank=True)
    Phone = models.CharField(max_length=30,blank=True)
    FAX = models.CharField(max_length=30,blank=True)

class supplier_addresses(models.Model):
    Supplier = models.ForeignKey(supplier_details,on_delete=models.CASCADE,related_name='supplier_addresses')
    Address = models.TextField(blank=True)
    City = models.CharField(max_length=50,blank=True)
    State = models.CharField(max_length=50,blank=True)
    Country = models.CharField(max_length=50,blank=True)

class supplier_email_messages(models.Model):
    Supplier = models.ForeignKey(supplier_details,on_delete=models.CASCADE,related_name='supplier_email_messages')
    Email = models.TextField(blank=True)
    Time = models.DateTimeField(blank=True,null=True)

class supplier_media(models.Model):
    Supplier = models.ForeignKey(supplier_details,on_delete=models.CASCADE,related_name='supplier_media')
    Document = models.FileField(null=True,blank=True,upload_to='Supplier_documents/')
    Image = models.FileField(null=True,blank=True,upload_to='Supplier_images/')

class Sell_products(models.Model):
    Supplier = models.ForeignKey(supplier_details,on_delete=models.CASCADE,related_name='Sell_products')
    Sector = models.CharField(max_length=100,blank=True)
    Division = models.CharField(max_length=100,blank=True)
    Product_group = models.CharField(max_length=100,blank=True)
    Product_category = models.CharField(max_length=100,blank=True)
    Product = models.CharField(max_length=300,blank=True)
    HSN_code = models.CharField(max_length=10,blank=True)
    Factory_address = models.TextField(blank=True)
    Warehouse_address = models.TextField(blank=True)
    Min_order_quantity = models.CharField(max_length=30,blank=True)