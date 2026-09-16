from django.shortcuts import render, get_object_or_404
from django.core import serializers
from django.http import HttpResponse, JsonResponse

from main.models import Certification

# Create your views here.
def get_products(request):
    products = Certification.objects.all()
    products_json = serializers.serialize("json", products)

    return HttpResponse(products_json, content_type="application/json")

def get_product_by_id(request, id):
    product = get_object_or_404(Certification, pk=id)
    return JsonResponse({
        "id": str(product.id),
        "product_name": product.product_name,
        "certification": product.certification,
        "eco_rating": product.eco_rating,
        "expire_at": product.expire_at,
    })

def isCertified(request, id):
    product = get_object_or_404(Certification, pk=id)
    return JsonResponse({
        "certification": product.certification
    })