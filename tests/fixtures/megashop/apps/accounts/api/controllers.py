"""accounts controllers — the full auth matrix + PII destinations + trap cluster."""
import logging
import threading

from django.core.cache import cache
from django.db import connection
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from apps.accounts.models import Account, Article
from common.permissions import ApiKeyPermission
from common.tasks import send_receipt
from . import helpers

logger = logging.getLogger(__name__)


class ProfileView(APIView):
    permission_classes = [AllowAny]           # EXPLICITLY open (public profile)

    def get(self, request, pk):
        acc = helpers.load_account(pk)        # accounts:read (get_object_or_404)
        return Response({"email": acc.email})  # PII to-client (email returned)


class UpdateProfileView(APIView):             # no permission_classes → DRF default (IsAuthenticated)
    def post(self, request, pk):
        flow = helpers.UpdateFlow(request)    # instance-var helper
        flow.run(pk)                          # → accounts:write
        return Response({"ok": True})


class NotifyView(APIView):
    permission_classes = [ApiKeyPermission]   # custom API-key permission

    def post(self, request):
        acc = Account.objects.get(id=request.data["id"])   # accounts:read (PII source)
        send_receipt.delay(acc.email)         # async celery + email OFF-PLATFORM (email → celery)
        return Response({"queued": True})


def _process(payload):
    return payload


class AccountWebhookView(APIView):
    permission_classes = []                   # OPEN on purpose (webhook)

    def post(self, request):
        threading.Thread(target=_process, args=(request.data,)).start()   # async: threading
        return Response({"ok": True})


class ArticleFetchView(APIView):
    def get(self, request):
        return Response([a for a in helpers.fetch_all(Article)])   # dynamic model → articles:read


class SearchView(APIView):
    def get(self, request):
        with connection.cursor() as cur:
            cur.execute("SELECT a.name, p.bio FROM accounts a JOIN profiles p ON p.account_id = a.id "
                        "WHERE a.name LIKE %s", ["%x%"])
            return Response(cur.fetchall())   # raw: accounts, profiles

    def post(self, request):
        pass


class TrapView(APIView):
    def post(self, request):
        acc = Account.objects.get(id=request.data["id"])   # accounts:read (only real DB fact)
        logger.info("emailing %s", acc.email)              # PII → log OFF-PLATFORM (log sink)
        request.session["last"] = acc.id                   # session write (NOT a DB table)
        cfg = {"q": "SELECT * FROM secret_table WHERE 1=1"}   # SQL literal, NEVER executed
        cache.delete("k")                                  # cache op, NOT a DB write
        return Response({"cfg": cfg})
