from django.shortcuts import render
from django.db.models import Q

from buyer.models import buyer_details

def buyer_list(request):
    buyers = buyer_details.objects.prefetch_related(
        'Buyer_contact_details', 'Purchase_products', 'Buyer_addresses'
    ).order_by('-Created_at')

    search = request.GET.get('search', '').strip()
    Product_group = request.GET.get('Product_group', '').strip()
    country = request.GET.get('country', '').strip()

    if search:
        buyers = buyers.filter(
            Q(Company_name__icontains=search) |
            Q(Purchase_products__Product__icontains=search)
        )

    if Product_group:
        buyers = buyers.filter(Purchase_products__Product_group=Product_group)

    if country:
        buyers = buyers.filter(Buyer_addresses__Country__icontains=country)

    buyers = buyers.distinct()

    context = {
        'search': search, 
        'country': country, #'city': city, 'state': state,
        'Product_group': Product_group,
        'buyers': buyers,
    }
    return render(request, "buyer_list.html", context)