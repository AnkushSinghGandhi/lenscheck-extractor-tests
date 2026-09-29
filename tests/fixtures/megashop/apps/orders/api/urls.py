from django.urls import path
from . import controllers as c

urlpatterns = [
    path("orders/", c.OrderListView.as_view()),
    path("orders/create/", c.OrderCreateView.as_view()),
    path("orders/<int:order_id>/", c.OrderDetailView.as_view()),
    path("orders/import/", c.OrderImportView.as_view()),
    path("orders/form-create/", c.OrderCreateFormView.as_view()),
]
