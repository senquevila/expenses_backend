# Django Imports
from django.urls import include, path

# DRF imports
from rest_framework.routers import DefaultRouter

# Model Imports
from expenses import api as api_views

router = DefaultRouter()
router.register(r"accounts", api_views.AccountViewSet, basename="api-accounts")
router.register(r"currencies", api_views.CurrencyViewSet, basename="api-currencies")
router.register(r"currency_converts", api_views.CurrencyConvertViewSet, basename="api-currency_converts")
router.register(r"loans", api_views.LoanViewSet, basename="api-loans")
router.register(r"periods", api_views.PeriodViewSet, basename="api-periods")
router.register(r"subscriptions", api_views.SubscriptionViewSet, basename="api-subscriptions")
router.register(r"transactions", api_views.TransactionViewSet, basename="api-expenses")
router.register(r"uploads", api_views.UploadViewSet, basename="api-uploads")
router.register(r"associations", api_views.AccountAssociationViewSet, basename="api-account_assoc")
router.register(r"program_transactions", api_views.ProgramTransactionViewSet, basename="api-program-transactions")

urlpatterns = [
    path("", include(router.urls)),
    # currencies
    path(
        "create_usd_exchange/",
        api_views.CreateDollarConversionView.as_view(),
        name="create-dollar-convert",
    ),
]
