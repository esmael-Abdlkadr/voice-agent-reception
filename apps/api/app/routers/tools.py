"""Per-workspace webhook tools the voice agent can call mid-conversation.

Each tool registers a webhook URL + a name/description the LLM uses to
decide when to invoke it. At call time the worker dynamically registers
each tool with the agent; when the LLM calls it, the worker POSTs the
query to the webhook and returns the response back to the LLM.

The "test" endpoint lets operators fire a sample request from the
dashboard to confirm their webhook is reachable.
"""
from __future__ import annotations

import time

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_session
from app.models import Tool, Workspace
from app.schemas import (
    ToolCreate,
    ToolDetail,
    ToolTestRequest,
    ToolTestResponse,
    ToolUpdate,
)
from app.services import auth_service

router = APIRouter(prefix="/workspaces/{workspace_id}/tools", tags=["tools"])


@router.get("", response_model=list[ToolDetail])
def list_tools(
    workspace: Workspace = Depends(auth_service.require_workspace_role("viewer")),
    session: Session = Depends(get_session),
) -> list[ToolDetail]:
    tools = (
        session.execute(
            select(Tool).where(Tool.workspace_id == workspace.id).order_by(Tool.created_at)
        )
        .scalars()
        .all()
    )
    return [ToolDetail.model_validate(t) for t in tools]


@router.post("", response_model=ToolDetail, status_code=status.HTTP_201_CREATED)
def create_tool(
    payload: ToolCreate,
    workspace: Workspace = Depends(auth_service.require_workspace_role("admin")),
    session: Session = Depends(get_session),
) -> ToolDetail:
    existing = session.execute(
        select(Tool).where(Tool.workspace_id == workspace.id, Tool.name == payload.name)
    ).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(
            status_code=409, detail=f"Tool name {payload.name!r} already exists in this workspace"
        )
    tool = Tool(workspace_id=workspace.id, **payload.model_dump())
    session.add(tool)
    session.commit()
    session.refresh(tool)
    return ToolDetail.model_validate(tool)


@router.get("/{tool_id}", response_model=ToolDetail)
def get_tool(
    tool_id: int,
    workspace: Workspace = Depends(auth_service.require_workspace_role("viewer")),
    session: Session = Depends(get_session),
) -> ToolDetail:
    tool = session.get(Tool, tool_id)
    if tool is None or tool.workspace_id != workspace.id:
        raise HTTPException(status_code=404, detail="Tool not found")
    return ToolDetail.model_validate(tool)


@router.patch("/{tool_id}", response_model=ToolDetail)
def update_tool(
    tool_id: int,
    payload: ToolUpdate,
    workspace: Workspace = Depends(auth_service.require_workspace_role("admin")),
    session: Session = Depends(get_session),
) -> ToolDetail:
    tool = session.get(Tool, tool_id)
    if tool is None or tool.workspace_id != workspace.id:
        raise HTTPException(status_code=404, detail="Tool not found")
    fields = payload.model_dump(exclude_unset=True)
    if "name" in fields and fields["name"] != tool.name:
        clash = session.execute(
            select(Tool).where(
                Tool.workspace_id == workspace.id,
                Tool.name == fields["name"],
                Tool.id != tool.id,
            )
        ).scalar_one_or_none()
        if clash is not None:
            raise HTTPException(status_code=409, detail="Tool name already in use")
    for key, value in fields.items():
        if value is not None:
            setattr(tool, key, value)
    session.commit()
    session.refresh(tool)
    return ToolDetail.model_validate(tool)


@router.delete("/{tool_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_tool(
    tool_id: int,
    workspace: Workspace = Depends(auth_service.require_workspace_role("admin")),
    session: Session = Depends(get_session),
) -> None:
    tool = session.get(Tool, tool_id)
    if tool is None or tool.workspace_id != workspace.id:
        raise HTTPException(status_code=404, detail="Tool not found")
    session.delete(tool)
    session.commit()


@router.post("/{tool_id}/test", response_model=ToolTestResponse)
def test_tool(
    tool_id: int,
    payload: ToolTestRequest,
    workspace: Workspace = Depends(auth_service.require_workspace_role("admin")),
    session: Session = Depends(get_session),
) -> ToolTestResponse:
    """Synchronously POST the configured webhook with a sample query and
    return whatever the webhook says. Used by the dashboard's 'Test' button
    so operators can confirm their endpoint is reachable."""
    tool = session.get(Tool, tool_id)
    if tool is None or tool.workspace_id != workspace.id:
        raise HTTPException(status_code=404, detail="Tool not found")

    headers = {"Content-Type": "application/json"}
    if tool.auth_header:
        headers["Authorization"] = tool.auth_header

    started = time.monotonic()
    try:
        response = httpx.post(
            tool.webhook_url,
            json={"query": payload.query},
            headers=headers,
            timeout=10.0,
        )
        duration_ms = int((time.monotonic() - started) * 1000)
        body = response.text
        return ToolTestResponse(
            status_code=response.status_code,
            response_body=body[:4096],
            error=None,
            duration_ms=duration_ms,
        )
    except Exception as exc:
        duration_ms = int((time.monotonic() - started) * 1000)
        return ToolTestResponse(
            status_code=0,
            response_body="",
            error=str(exc),
            duration_ms=duration_ms,
        )
