from django.shortcuts import render
from django.http import HttpResponse
# Create your views here.
import stripe
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Product,Payment,Invoice
from rest_framework import permissions
from .serializers import ProductSerializer
import logging

logger = logging.getLogger("shop.py")


stripe.api_key = settings.STRIPE_SECRETE_KEY

# ✅ List Products
class ProductListAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def get(self, request):
        products = Product.objects.all()
        logger.info("user requesting",request.user)
        serializer = ProductSerializer(products, many=True)
        return Response(serializer.data)
    

class CreateCheckoutSessionAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        try:
            product_id = request.data.get("product_id")
            product = Product.objects.get(id=product_id)

            # Create Payment record in DB
            payment = Payment.objects.create(
                user=request.user,
                product=product,
                amount=product.price,
                status="pending"
            )

            # Create Stripe Checkout Session
            session = stripe.checkout.Session.create(
                payment_method_types=["card"],
                line_items=[{
                    "price_data": {
                        "currency": "usd",
                        "unit_amount": int(product.price * 100),
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
                metadata={"payment_id": payment.id},  # 🔑 link to DB payment
            )

            # Save Checkout ID + Intent
            payment.stripe_checkout_id = session.id
            payment.stripe_payment_intent = session.payment_intent
            payment.save()

            return Response({"checkout_url": session.url})
        except Product.DoesNotExist:
            return Response({"error": "Product not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logging.error(str(e))
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)



class SuccessView(APIView):
    def get(self, request):
        return HttpResponse("Hi, your payment has been completed ")

class CancelView(APIView):
    def get(self, request):
        return HttpResponse("Hi, your payment was cancelled ")
    

from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse, HttpResponse

@csrf_exempt
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE")
    endpoint_secret = settings.STRIPE_WEBHOOK_SECRET  # replace with your Webhook Signing Secret from Stripe Dashboard


    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, endpoint_secret
        )
    except stripe.error.SignatureVerificationError:
        return HttpResponse(status=400)

   
    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        payment_id = session["metadata"].get("payment_id")
        try:
            payment = Payment.objects.get(id=payment_id)
            payment.status = "succeeded"
            payment.save()
        except Payment.DoesNotExist:
            pass

    if event["type"] == "payment_intent.payment_failed":
        intent = event["data"]["object"]
        metadata = intent.get("metadata", {})
        payment_id = metadata.get("payment_id")
        if payment_id:
            try:
                payment = Payment.objects.get(id=payment_id)
                payment.status = "failed"
                payment.save()
            except Payment.DoesNotExist:
                pass

    return HttpResponse(status=200)



class CreateInvoiceApiView(APIView):
    permission_classes =  [permissions.IsAuthenticated]

    def post(self,request):
        payment_id = request.data.get("payment_id")
        logger.info(payment_id)


        try:
            payment = Payment.objects.get(id = payment_id)

        except Payment.DoesNotExist:
            return Response({"error": "Payment not found"}, status=status.HTTP_404_NOT_FOUND)
        
        customer = stripe.Customer.create(
            email=request.user.email,
            name=request.user.username,
        )
        logger.info(payment)
          # Create Invoice Item
          # Create the Invoice
        invoice = stripe.Invoice.create(
            customer=customer.id,
            collection_method="send_invoice",  # or 'charge_automatically'
            days_until_due=7,
        )
        stripe.InvoiceItem.create(
            invoice=invoice.id,
            customer=customer.id,
            amount=int(payment.amount),
            currency='usd',
            description=f"Invoice for payment {payment.stripe_payment_intent}",
        )

      

        # Finalize the Invoice
        finalized = stripe.Invoice.finalize_invoice(invoice.id)

        # Save in DB
        invoice_obj = Invoice.objects.create(
            user=request.user,
            payment=payment,
            invoice_url=finalized.hosted_invoice_url,
            invoice_pdf=finalized.invoice_pdf,
        )

        return Response({
            "message": "Invoice created successfully",
            "invoice_url": invoice_obj.invoice_url,
            "invoice_pdf": invoice_obj.invoice_pdf
        }, status=status.HTTP_201_CREATED)
    
from google import genai

class GoogleChatappView(APIView):
    def get(self,request):
        

        client = genai.Client(api_key=settings.GEMINI_API_KEY)
        # prompt = request.data.get('prompt')

        # response = client.models.generate_content(
        #     model="gemini-2.0-flash", contents={prompt}
        # )
        response = client.models.generate_content(
            model="gemini-1.5-flash",  
            contents=[
                {"role": "user", "parts": "Explain bubble sort with example."}
            ],
            system_instruction="You are a strict computer science teacher. Always explain step by step, in detail, and provide Python code examples."
        )

        output_text = ""
        if hasattr(response, "candidates"):
            for candidate in response.candidates:
                for part in candidate.content.parts:
                    output_text += part.text + "\n"
        print(output_text) 
        return Response({"message":"getting data","data":{output_text}},status=status.HTTP_200_OK)