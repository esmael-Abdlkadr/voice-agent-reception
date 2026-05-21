from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.models import KnowledgeAnswerRequest, KnowledgeAnswerResponse, KnowledgeDocument, KnowledgeDocumentCreate, KnowledgeSearchRequest
from app.services import agent_service, auth_service, llm_service, store

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


@router.get("/documents")
def list_documents() -> list[KnowledgeDocument]:
    return list(store.knowledge_documents.values())


@router.post("/documents", status_code=status.HTTP_201_CREATED)
def create_document(payload: KnowledgeDocumentCreate, _user=Depends(auth_service.require_roles("platform_admin", "campaign_operator"))) -> KnowledgeDocument:
    document = KnowledgeDocument(id=store.next_id("doc"), **payload.model_dump())
    store.knowledge_documents[document.id] = document
    return document


@router.get("/documents/{document_id}")
def get_document(document_id: str) -> KnowledgeDocument:
    if document_id not in store.knowledge_documents:
        raise HTTPException(status_code=404, detail="Knowledge document not found")
    return store.knowledge_documents[document_id]


@router.delete("/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(document_id: str, _user=Depends(auth_service.require_roles("platform_admin"))) -> Response:
    if document_id not in store.knowledge_documents:
        raise HTTPException(status_code=404, detail="Knowledge document not found")
    del store.knowledge_documents[document_id]
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/search")
def search(payload: KnowledgeSearchRequest) -> dict[str, list[dict]]:
    return {"results": agent_service.search_knowledge(payload.query)}


@router.post("/answer")
def answer(payload: KnowledgeAnswerRequest) -> KnowledgeAnswerResponse:
    results = agent_service.search_knowledge(payload.query)
    answer_text, llm_meta = llm_service.answer_with_knowledge(payload.query, results, payload.max_context_items)
    return KnowledgeAnswerResponse(query=payload.query, answer=answer_text, llm=llm_meta, results=results[: payload.max_context_items])
