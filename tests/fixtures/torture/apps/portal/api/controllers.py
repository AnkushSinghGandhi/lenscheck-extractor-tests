"""portal controllers — celery, threading, dynamic model, boto3/S3 egress, raw SQL, and a trap
cluster (log egress / session write / SQL-string-in-a-dict) that must NOT become DB facts."""
import logging
import threading

import boto3
from django.conf import settings
from django.core.cache import cache
from django.db import connection
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.portal.models import User, Article
from . import helpers
from .tasks import send_receipt

logger = logging.getLogger(__name__)


class UserProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        user = helpers.load_user(pk)                 # users:read (get_object_or_404), PII source
        return Response({"name": user.display_name})


class NotifyView(APIView):
    def post(self, request):
        user = User.objects.get(id=request.data["user"])     # users:read
        send_receipt.delay(user.email)                       # celery async + email → PII egress
        return Response({"queued": True})


def _process(payload):
    return payload


class WebhookView(APIView):
    def post(self, request):
        threading.Thread(target=_process, args=(request.data,)).start()   # threading async
        return Response({"ok": True})


class ArticleFetchView(APIView):
    def get(self, request):
        return Response([a for a in helpers.fetch_all(Article)])   # dynamic model → articles (param bind)


class SearchView(APIView):
    def get(self, request):
        with connection.cursor() as cur:
            cur.execute("SELECT a.title, d.host FROM articles a "
                        "JOIN domains d ON d.id = a.domain_id WHERE a.title LIKE %s", ["%x%"])
            return Response(cur.fetchall())              # raw: articles, domains


class MediaExportView(APIView):
    def post(self, request):
        rows = list(User.objects.values("id"))          # users:read
        boto3.client("s3").put_object(Bucket=settings.S3_BUCKET, Key="dump", Body=b"")   # external S3
        return Response({"n": len(rows)})


class CacheOnlyView(APIView):
    def get(self, request):
        v = cache.get("home")                 # cache:read
        cache.set("home", 1)                  # cache:write
        cache.delete("home")                  # cache:write — NOT a DB table write (trap)
        return Response({"v": v})


class UpsertView(APIView):
    def post(self, request):
        user, created = User.objects.get_or_create(email=request.data["email"])   # users:write
        return Response({"id": user.id, "new": created})


class DynamicReportView(APIView):
    def get(self, request):
        table = request.GET["t"]
        with connection.cursor() as cur:
            cur.execute(f"SELECT * FROM {table} LIMIT 10")   # TRAP: dynamic table → NO table fact
        return Response({})


class TrapView(APIView):
    def post(self, request):
        user = User.objects.get(id=request.data["user"])         # users:read (the only real DB fact)
        logger.info("emailing %s", user.email)                   # PII → log sink (not a table)
        request.session["last"] = user.id                        # session write (NOT a DB table)
        cfg = {"q": "SELECT * FROM secret_table WHERE 1=1"}      # SQL literal, NEVER executed
        return Response({"cfg": cfg})
