from django.db import models
from buyer.models import buyer_details

class Enquiry_details(models.Model):
    Custom_id = models.CharField(max_length=15,blank=True)
    Company_name = models.CharField(max_length=150,blank=True)
    buyer = models.ForeignKey(buyer_details, on_delete=models.SET_NULL,null=True, blank=True, related_name='Enquiry_details')
    Description = models.TextField(blank=True)
    Enquiry_date = models.DateField(blank=True,null=True)
    Closing_date = models.DateField(blank=True,null=True)
    Enquiry_type = models.CharField(max_length=50,blank=True)
    Admin_remark = models.TextField(blank=True)

class Enquiry_media(models.Model):
    Enquiry = models.ForeignKey(Enquiry_details,on_delete=models.CASCADE,related_name='Enquiry_media')
    Document = models.FileField(null=True,blank=True,upload_to='Enquiry_documents/')
    Image = models.FileField(null=True,blank=True,upload_to='Enquiry_images/')

class Enquiry_email_messages(models.Model):
    Enquiry = models.ForeignKey(Enquiry_details,on_delete=models.CASCADE,related_name='Enquiry_email_messages')
    To = models.EmailField(blank=True)
    Subject = models.TextField(blank=True)
    Body = models.TextField(blank=True)
    Time = models.DateTimeField(blank=True,null=True)

class Enquiry_products(models.Model):
    Supplier = models.ForeignKey(Enquiry_details,on_delete=models.CASCADE,related_name='Enquiry_products')
    Sector = models.CharField(max_length=100,blank=True)
    Division = models.CharField(max_length=100,blank=True)
    Product_group = models.CharField(max_length=100,blank=True)
    Product_category = models.CharField(max_length=100,blank=True)
    Product = models.CharField(max_length=100,blank=True)
    HSN_code = models.CharField(max_length=10,blank=True)
    Billing_address = models.TextField(blank=True)
    Delivery_address = models.TextField(blank=True)
    Quantity = models.CharField(max_length=20,blank=True)
    Packaging = models.CharField(max_length=200,blank=True)
    Target_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    Currency = models.CharField(max_length=5,blank=True)