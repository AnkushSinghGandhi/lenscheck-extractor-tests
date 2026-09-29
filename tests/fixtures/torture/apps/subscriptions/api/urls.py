from django.urls import path
from .landing.controllers import SubscriptionLandingView, SubscriptionSummaryView
from .dashboard.controllers import SubscriptionDashboardView
from .payment.controllers import PurchaseCheckView, SubscriptionPurchaseView
from .registration.controllers import RegistrationView

urlpatterns = [
    path("subscriptions/landing/", SubscriptionLandingView.as_view()),
    path("subscriptions/<int:lead_id>/summary/", SubscriptionSummaryView.as_view()),
    path("subscriptions/<int:lead_id>/dashboard/", SubscriptionDashboardView.as_view()),
    path("subscriptions/<int:lead_id>/purchase-check/", PurchaseCheckView.as_view()),
    path("subscriptions/purchase/", SubscriptionPurchaseView.as_view()),
    path("subscriptions/register/", RegistrationView.as_view()),
]
