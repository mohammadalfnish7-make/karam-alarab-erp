from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request

from application.actor import Actor
from domain.shared.domain_error import ForbiddenError
from notify.api.deps import require_permission
from notify.application.delivery_worker import process_pending_deliveries

router = APIRouter(tags=["notify-delivery"])


@router.post("/work/process-deliveries")
def process_work_deliveries(
    request: Request,
    _: Annotated[Actor, Depends(require_permission("work:admin"))],
) -> dict[str, int]:
    """Dev/test only: pump pending webhook deliveries once (path kept for clients)."""
    settings = request.app.state.settings
    if settings.is_production:
        raise ForbiddenError(
            "Delivery processing is not exposed over HTTP in production."
        )
    processed = process_pending_deliveries(
        request.app.state.session_factory,
        trace_recorder=getattr(request.app.state, "trace_recorder", None),
    )
    return {"processed": processed}
