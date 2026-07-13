from django.shortcuts import render

def buyer_list(request):
    return render(request,"buyer_list.html")