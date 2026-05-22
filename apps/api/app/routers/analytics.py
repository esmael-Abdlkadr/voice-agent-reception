"""Per-workspace analytics rollups.

V1 computes everything from the calls table at request time. For ~10k
calls per workspace this is fine; if a workspace ever crosses ~100k we'll
either pre-aggregate into a daily-rollup table or run these queries on a
materialized view.

All time bucketing is UTC for now.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import get_session
from app.models import Call, CallToolCall, Workspace
from app.schemas import (
    AnalyticsDailyPoint,
    AnalyticsStatusBreakdown,
    AnalyticsToolCount,
    WorkspaceAnalytics,
)
from app.services import auth_service

router = APIRouter(prefix="/workspaces/{workspace_id}/analytics", tags=["analytics"])


@router.get("", response_model=WorkspaceAnalytics)
def workspace_analytics(
    days: int = Query(default=30, ge=1, le=365),
    workspace: Workspace = Depends(auth_service.require_workspace_role("viewer")),
    session: Session = Depends(get_session),
) -> WorkspaceAnalytics:
    now = datetime.now(timezone.utc)
    window_start = (now - timedelta(days=days - 1)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )

    calls = (
        session.execute(
            select(Call)
            .where(Call.workspace_id == workspace.id, Call.started_at >= window_start)
            .order_by(Call.started_at)
        )
        .scalars()
        .all()
    )

    total = len(calls)
    by_status = AnalyticsStatusBreakdown()
    durations: list[int] = []
    for c in calls:
        if c.status == "completed":
            by_status.completed += 1
        elif c.status == "active":
            by_status.active += 1
        elif c.status == "escalated":
            by_status.escalated += 1
        elif c.status == "failed":
            by_status.failed += 1
        if c.duration_ms is not None and c.status in ("completed", "escalated"):
            durations.append(c.duration_ms)

    avg_duration_ms = round(sum(durations) / len(durations)) if durations else None

    # Per-day buckets — emit every day in the window (zero-filled).
    by_day_counter: Counter[str] = Counter()
    for c in calls:
        bucket = c.started_at.astimezone(timezone.utc).strftime("%Y-%m-%d")
        by_day_counter[bucket] += 1
    by_day: list[AnalyticsDailyPoint] = []
    for offset in range(days):
        day = (window_start + timedelta(days=offset)).strftime("%Y-%m-%d")
        by_day.append(AnalyticsDailyPoint(date=day, count=by_day_counter.get(day, 0)))

    # Top tools — joined from CallToolCall scoped to this window.
    tool_rows = session.execute(
        select(CallToolCall.tool_name, func.count(CallToolCall.id))
        .join(Call, Call.id == CallToolCall.call_id)
        .where(Call.workspace_id == workspace.id, Call.started_at >= window_start)
        .group_by(CallToolCall.tool_name)
        .order_by(func.count(CallToolCall.id).desc())
        .limit(10)
    ).all()
    top_tools = [
        AnalyticsToolCount(tool_name=name, count=count) for name, count in tool_rows
    ]

    # Completion rate: completed vs everything except `active`. Active calls
    # are excluded from the denominator because they haven't finished yet.
    finished = by_status.completed + by_status.escalated + by_status.failed
    completion_rate = (by_status.completed / finished) if finished > 0 else 0.0

    return WorkspaceAnalytics(
        window_days=days,
        total_calls=total,
        avg_duration_ms=avg_duration_ms,
        completion_rate=completion_rate,
        by_status=by_status,
        by_day=by_day,
        top_tools=top_tools,
    )
