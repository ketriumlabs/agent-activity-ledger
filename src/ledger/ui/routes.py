from __future__ import annotations

from datetime import datetime
from importlib import resources
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from ledger.api.deps import get_repository
from ledger.store.repository import EventRepository

router = APIRouter(tags=["ui"], include_in_schema=False)

_templates_dir = resources.files("ledger.ui").joinpath("templates")
templates = Jinja2Templates(directory=str(_templates_dir))


@router.get("/", response_class=HTMLResponse)
def timeline(
    request: Request,
    repo: Annotated[EventRepository, Depends(get_repository)],
    agent: str | None = None,
    type: str | None = None,  # noqa: A002
    money: bool = False,
) -> HTMLResponse:
    events = repo.query(agent=agent, action_type=type, money_only=money, limit=200)
    agents = sorted({e.actor.agent for e in repo.query(limit=200)})
    return templates.TemplateResponse(
        request,
        "timeline.html",
        {
            "events": events,
            "agents": agents,
            "filter_agent": agent or "",
            "filter_type": type or "",
            "filter_money": money,
            "now": datetime.now().isoformat(),
        },
    )
