from django.shortcuts import render

def edit_enquiry(request, sp_id):
    return render(request,'edit_enquiry.html', sp_id)
