"""Knowledge base endpoints scoped per workspace.

Upload accepts txt/md/pdf up to ~10MB. Ingestion (chunk + embed + Qdrant
upsert) happens in a background task so the HTTP request returns
immediately with status="processing". The client polls (or the future
WebSocket pushes) until status flips to "ready" or "failed".
"""
from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_session
from app.models import KnowledgeDoc, User, Workspace
from app.schemas import (
    KnowledgeDocPublic,
    KnowledgeSearchHit,
    KnowledgeSearchRequest,
    KnowledgeSearchResponse,
)
from app.services import auth_service, knowledge_service

router = APIRouter(prefix="/workspaces/{workspace_id}/knowledge", tags=["knowledge"])

MAX_BYTES = 10 * 1024 * 1024  # 10 MB
ALLOWED_EXTENSIONS = {".txt", ".md", ".pdf"}


@router.get("", response_model=list[KnowledgeDocPublic])
def list_docs(
    workspace: Workspace = Depends(auth_service.require_workspace_role("viewer")),
    session: Session = Depends(get_session),
) -> list[KnowledgeDocPublic]:
    docs = (
        session.execute(
            select(KnowledgeDoc)
            .where(KnowledgeDoc.workspace_id == workspace.id)
            .order_by(KnowledgeDoc.created_at.desc())
        )
        .scalars()
        .all()
    )
    return [KnowledgeDocPublic.model_validate(d) for d in docs]


@router.post(
    "",
    response_model=KnowledgeDocPublic,
    status_code=status.HTTP_202_ACCEPTED,
)
async def upload_doc(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    workspace: Workspace = Depends(auth_service.require_workspace_role("admin")),
    user: User = Depends(auth_service.current_user),
    session: Session = Depends(get_session),
) -> KnowledgeDocPublic:
    filename = (file.filename or "").strip() or "untitled"
    lower = filename.lower()
    extension = "." + lower.rsplit(".", 1)[-1] if "." in lower else ""
    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file type {extension!r}. Allowed: {sorted(ALLOWED_EXTENSIONS)}",
        )

    content = await file.read()
    if len(content) == 0:
        raise HTTPException(status_code=400, detail="Empty file")
    if len(content) > MAX_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File too large; max {MAX_BYTES // (1024 * 1024)} MB",
        )

    doc = KnowledgeDoc(
        workspace_id=workspace.id,
        filename=filename,
        content_type=file.content_type or "",
        size_bytes=len(content),
        status="processing",
        chunk_count=0,
        uploaded_by_user_id=user.id,
    )
    session.add(doc)
    session.commit()
    session.refresh(doc)

    background_tasks.add_task(knowledge_service.ingest_document_bg, doc.id, content)
    return KnowledgeDocPublic.model_validate(doc)


@router.get("/{doc_id}", response_model=KnowledgeDocPublic)
def get_doc(
    doc_id: int,
    workspace: Workspace = Depends(auth_service.require_workspace_role("viewer")),
    session: Session = Depends(get_session),
) -> KnowledgeDocPublic:
    doc = session.get(KnowledgeDoc, doc_id)
    if doc is None or doc.workspace_id != workspace.id:
        raise HTTPException(status_code=404, detail="Document not found")
    return KnowledgeDocPublic.model_validate(doc)


@router.delete("/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_doc(
    doc_id: int,
    workspace: Workspace = Depends(auth_service.require_workspace_role("admin")),
    session: Session = Depends(get_session),
) -> None:
    doc = session.get(KnowledgeDoc, doc_id)
    if doc is None or doc.workspace_id != workspace.id:
        raise HTTPException(status_code=404, detail="Document not found")
    knowledge_service.delete_document_vectors(workspace.id, doc.id)
    session.delete(doc)
    session.commit()


@router.post("/search", response_model=KnowledgeSearchResponse)
def search_kb(
    payload: KnowledgeSearchRequest,
    workspace: Workspace = Depends(auth_service.require_workspace_role("viewer")),
) -> KnowledgeSearchResponse:
    raw_hits = knowledge_service.search(
        workspace_id=workspace.id, query=payload.query, limit=payload.limit
    )
    return KnowledgeSearchResponse(
        query=payload.query,
        hits=[KnowledgeSearchHit(**h) for h in raw_hits],
    )
