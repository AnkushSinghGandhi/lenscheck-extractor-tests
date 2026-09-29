"""Flask + SQLAlchemy analytics service — routes on a blueprint, SQLAlchemy session ops, boto3/sendgrid."""
import boto3
import requests
import sendgrid
from flask import Blueprint
from flask_login import login_required
from sqlalchemy import insert
from django.conf import settings

from .db import session
from .models_sa import Metric, Visit, Report

bp = Blueprint("analytics", __name__, url_prefix="/analytics")


@bp.route("/metrics")
def metrics_list():
    return session.query(Metric).filter(Metric.id > 0).all()      # metrics:read  (no auth → ?)


@bp.route("/summary")
@login_required
def summary():
    return Metric.query.filter_by(active=True).all()              # metrics:read (declarative), auth=login_required


@bp.route("/ingest", methods=["POST"])
def ingest():
    v = Visit(email="x@y.com")
    session.add(v)                                                # visits:write
    requests.post(settings.ANALYTICS_URL, json={"email": v.email})   # external + PII OFF-PLATFORM
    return {}


@bp.route("/export", methods=["POST"])
def export_reports():
    session.execute(insert(Report))                              # reports:write (SQLAlchemy 2.x core)
    boto3.client("s3").put_object(Bucket=settings.S3_BUCKET, Key="rep", Body=b"")   # external: S3
    return {}


@bp.route("/email", methods=["POST"])
def email_report():
    sendgrid.SendGridAPIClient().send({"to": "ops@x.com"})       # external: sendgrid
    return {}
