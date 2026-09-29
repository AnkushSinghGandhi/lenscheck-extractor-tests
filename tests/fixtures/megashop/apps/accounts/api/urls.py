from django.urls import path
from . import controllers as c

urlpatterns = [
    path("accounts/<int:pk>/", c.ProfileView.as_view()),
    path("accounts/<int:pk>/update/", c.UpdateProfileView.as_view()),
    path("accounts/notify/", c.NotifyView.as_view()),
    path("accounts/webhook/", c.AccountWebhookView.as_view()),
    path("accounts/articles/", c.ArticleFetchView.as_view()),
    path("accounts/search/", c.SearchView.as_view()),
    path("accounts/misc/", c.TrapView.as_view()),
]
