from django.db import models

class buyer_details(models.Model):
    Custom_id = models.CharField(max_length=15,blank=True)
    Company_name = models.CharField(max_length=150,blank=True)
    Description = models.TextField(blank=True)
    Website_link = models.CharField(max_length=100,blank=True)
    GST_number = models.CharField(max_length=20,blank=True)
    IEC_code = models.CharField(max_length=15,blank=True)
    PAN_number = models.CharField(max_length=15,blank=True)
    DIN_number = models.CharField(max_length=25,blank=True)
    CIN_number = models.CharField(max_length=30,blank=True)
    DB_number = models.CharField(max_length=30,blank=True)
    Contact_person = models.CharField(max_length=100,blank=True)
    Payment_terms = models.TextField(blank=True)
    Supplier_preferences = models.TextField(blank=True)
    Transport_preferences = models.TextField(blank=True)
    Monthly_requirements = models.TextField(blank=True)
    Admin_remark = models.TextField(blank=True)
    Created_at = models.DateField(null=True,blank=True)

class Buyer_contact_details(models.Model):
    Buyer = models.ForeignKey(buyer_details,on_delete=models.CASCADE,related_name='Buyer_contact_details')
    Email = models.EmailField(blank=True)
    Phone = models.CharField(max_length=20,blank=True)
    Note = models.TextField(blank=True)

class Buyer_addresses(models.Model):
    Buyer = models.ForeignKey(buyer_details,on_delete=models.CASCADE,related_name='Buyer_addresses')
    Address = models.TextField(blank=True)
    City = models.CharField(max_length=50,blank=True)
    State = models.CharField(max_length=50,blank=True)
    Country = models.CharField(max_length=50,blank=True)

class Buyer_email_messages(models.Model):
    Buyer = models.ForeignKey(buyer_details,on_delete=models.CASCADE,related_name='Buyer_email_messages')
    Email = models.TextField(blank=True)
    Time = models.DateTimeField(blank=True,null=True)

class Buyer_media(models.Model):
    Buyer = models.ForeignKey(buyer_details,on_delete=models.CASCADE,related_name='Buyer_media')
    Document = models.FileField(null=True,blank=True,upload_to='Buyer_documents/')
    Image = models.FileField(null=True,blank=True,upload_to='Buyer_images/')

class Purchase_products(models.Model):
    Buyer = models.ForeignKey(buyer_details,on_delete=models.CASCADE,related_name='Purchase_products')
    Sector = models.CharField(max_length=100,blank=True)
    Division = models.CharField(max_length=100,blank=True)
    Product_group = models.CharField(max_length=100,blank=True)
    Product_category = models.CharField(max_length=100,blank=True)
    Product = models.CharField(max_length=100,blank=True)
    HSN_code = models.CharField(max_length=10,blank=True)
    Billing_address = models.TextField(blank=True)
    Delivery_address = models.TextField(blank=True)