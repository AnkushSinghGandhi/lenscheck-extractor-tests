from django.urls import path
from . import controllers as c

urlpatterns = [
    path("catalog/", c.CatalogListView.as_view()),
    path("catalog/categories/", c.CategorySummaryView.as_view()),
    path("catalog/cache/clear/", c.CacheClearView.as_view()),
]
