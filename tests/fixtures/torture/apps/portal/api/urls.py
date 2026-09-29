from django.urls import path
from . import controllers as c

urlpatterns = [
    path("portal/users/<int:pk>/", c.UserProfileView.as_view()),
    path("portal/notify/", c.NotifyView.as_view()),
    path("portal/webhook/", c.WebhookView.as_view()),
    path("portal/articles/", c.ArticleFetchView.as_view()),
    path("portal/search/", c.SearchView.as_view()),
    path("portal/media/export/", c.MediaExportView.as_view()),
    path("portal/cache-demo/", c.CacheOnlyView.as_view()),
    path("portal/upsert/", c.UpsertView.as_view()),
    path("portal/report/dynamic/", c.DynamicReportView.as_view()),
    path("portal/misc/", c.TrapView.as_view()),
]
