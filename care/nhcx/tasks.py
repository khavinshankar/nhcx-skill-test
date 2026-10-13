"""NHCX background work (G1, SCAFFOLDING 7): token refresh every minute, ledger
pruning hourly, and the startup checks once a worker is up.

Only the instance with `NHCX_ROLE` set does this work, and only when the gateway
is configured; everywhere else the tasks are no-ops.
"""

from __future__ import annotations

import logging

from celery import Celery, current_app, shared_task
from celery.signals import worker_ready
from django.conf import settings

logger = logging.getLogger("care.nhcx.gateway")


def _gateway():
    if not getattr(settings, "NHCX_ROLE", False):
        return None
    if not (getattr(settings, "NHCX_GATEWAY_CONFIG", "") or "").strip():
        return None
    from care.nhcx.gateway import gateway_status

    gw, cause = gateway_status()
    if gw is None:
        logger.warning("nhcx: gateway not configured: %s", cause)
    return gw


@shared_task(name="care.nhcx.tasks.refresh_tokens", ignore_result=True)
def refresh_tokens() -> int | None:
    gw = _gateway()
    if gw is None:
        return None
    return gw.refresh_all()


@shared_task(name="care.nhcx.tasks.prune_ledger", ignore_result=True)
def prune_ledger() -> int | None:
    gw = _gateway()
    if gw is None or not gw.ledger.enabled:
        return None
    return gw.sweep()


@shared_task(name="care.nhcx.tasks.check_gateway", ignore_result=True)
def check_gateway() -> None:
    gw = _gateway()
    if gw is None:
        return
    gw.refresh_all()
    gw.sweep()
    gw.check()


@worker_ready.connect
def _on_worker_ready(sender=None, **kwargs):
    if getattr(settings, "NHCX_ROLE", False) and getattr(
        settings, "NHCX_GATEWAY_CONFIG", ""
    ):
        check_gateway.delay()


@current_app.on_after_finalize.connect
def setup_periodic_tasks(sender: Celery, **kwargs):
    if not getattr(settings, "NHCX_GATEWAY_CONFIG", ""):
        return
    sender.add_periodic_task(60.0, refresh_tokens.s(), name="nhcx_refresh_tokens")
    sender.add_periodic_task(3600.0, prune_ledger.s(), name="nhcx_prune_ledger")
