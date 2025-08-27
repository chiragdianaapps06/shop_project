from django.shortcuts import render
from django.http import HttpResponse
# Create your views here.
import stripe
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Product
from .serializers import ProductSerializer

stripe.api_key = settings.STRIPE_SECRETE_KEY

# ✅ List Products
class ProductListAPIView(APIView):
    def get(self, request):
        products = Product.objects.all()
        serializer = ProductSerializer(products, many=True)
        return Response(serializer.data)
    


class CreateCheckoutSessionAPIView(APIView):
    def post(self, request, *args, **kwargs):
        try:
            product_id = request.data.get("product_id")
            product = Product.objects.get(id=product_id)
            print(product)

            # Create Stripe Checkout Session
            session = stripe.checkout.Session.create(
                payment_method_types=["card"],
                line_items=[{
                    "price_data": {
                        "currency": "usd",
                        "unit_amount": int(product.price * 100),  # cents
                        "product_data": {
                            "name": product.name,
                            "description": product.description,
                        },
                    },
                    "quantity": 1,
                }],
                mode="payment",
                success_url="http://localhost:8000/api/payment/success/",
                cancel_url="http://localhost:8000/api/payment/cancel/",
            )

            return Response({"checkout_url": session.url})
        except Product.DoesNotExist:
            return Response({"error": "Product not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        



class SuccessView(APIView):
    def get(self, request):
        return HttpResponse("Hi, your payment has been completed ")

class CancelView(APIView):
    def get(self, request):
        return HttpResponse("Hi, your payment was cancelled ")