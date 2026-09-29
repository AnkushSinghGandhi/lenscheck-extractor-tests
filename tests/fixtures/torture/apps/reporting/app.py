"""Flask + SQLAlchemy app (routes on decorators, not urls.py; a blueprint carries the prefix).
Exercises the framework-agnostic path: SQLAlchemy session.query / .add / .execute / Model.query."""
import requests
from flask import Blueprint
from flask_login import login_required
from sqlalchemy import insert

from .db import session
from .models_sa import Metric, Visit

bp = Blueprint("reporting", __name__, url_prefix="/reporting")


@bp.route("/metrics")
def metrics_list():
    return session.query(Metric).filter(Metric.id > 0).all()      # metrics:read


@bp.route("/summary")
@login_required
def summary():
    return Metric.query.filter_by(active=True).all()              # metrics:read (declarative query), auth


@bp.route("/ingest", methods=["POST"])
def ingest():
    v = Visit(email="x@y.com")
    session.add(v)                                                # visits:write
    requests.post("https://analytics.example.com/track", json={"email": v.email})   # external + PII egress
    return {}


@bp.route("/bulk", methods=["POST"])
def bulk_ingest():
    session.execute(insert(Visit))                               # visits:write (SQLAlchemy 2.x core)
    return {}
