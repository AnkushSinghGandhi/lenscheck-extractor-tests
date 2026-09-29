from django.urls import path
from . import controllers as c

urlpatterns = [
    path("ads/campaigns/", c.CampaignListView.as_view()),
    path("ads/campaigns/export/", c.CampaignExportView.as_view()),
    path("ads/campaigns/import/", c.CampaignImportView.as_view()),
    path("ads/campaigns/create/", c.CampaignCreateView.as_view()),
    path("ads/<str:kind>/<int:pk>/interactions/export/", c.EntityInteractionsExportView.as_view()),
    path("ads/<str:kind>/metrics/", c.EntityMetricsView.as_view()),
    path("ads/campaigns/raw/", c.CampaignRawView.as_view()),
    path("ads/audit/purge/", c.AuditPurgeView.as_view()),
]
