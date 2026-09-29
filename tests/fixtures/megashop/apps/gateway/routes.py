"""FastAPI gateway — routes on decorators with a router prefix; Depends auth; httpx egress; celery."""
import httpx
from fastapi import APIRouter, Depends
from celery import current_app

router = APIRouter(prefix="/gw")


def get_current_user():
    return {"id": 1}


@router.get("/status")
def status():
    return {"ok": True}                                      # health — no auth, no facts


@router.get("/proxy-order")
def proxy_order(user=Depends(get_current_user)):             # auth: FastAPI dependency
    httpx.get("https://upstream.example.com/orders")        # external: httpx
    return {}


@router.post("/dispatch")
def dispatch():
    current_app.send_task("worker.process_batch")           # async: celery send_task
    return {}


@router.post("/webhook")
def gw_webhook():
    httpx.post("https://hooks.example.com/in", json={})     # external: httpx
    return {}
