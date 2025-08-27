from django.urls import path
from .views import ProductListAPIView,CreateCheckoutSessionAPIView,SuccessView,CancelView

urlpatterns = [
    path("products/", ProductListAPIView.as_view(), name="product-list"),
    path("create-checkout-session/", CreateCheckoutSessionAPIView.as_view(), name="checkout-session"),
    path('payment/success/',SuccessView.as_view(),name='payment-successful'),
    path('payment/cancel/',CancelView.as_view(),name='payment-cancel')
]
