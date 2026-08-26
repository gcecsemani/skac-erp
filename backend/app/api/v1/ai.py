"""AI assistant: natural-language business Q&A over vetted tools (no raw SQL)."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core import rbac
from app.core.database import get_db
from app.core.deps import CurrentUser, require_permission
from app.schemas.sales import AskRequest, AskResponse
from app.services.ai import assistant, tools

router = APIRouter(prefix="/ai", tags=["ai"])


@router.get("/tools")
def list_tools(_: CurrentUser = Depends(require_permission(rbac.P_AI_USE))) -> dict:
    """Expose the vetted tool catalogue (transparency / debugging)."""
    return {
        name: {"description": t.description, "parameters": t.parameters}
        for name, t in tools.TOOLS.items()
    }


@router.post("/ask", response_model=AskResponse)
def ask(
    payload: AskRequest,
    current: CurrentUser = Depends(require_permission(rbac.P_AI_USE)),
    db: Session = Depends(get_db),
) -> AskResponse:
    # Resolve branch scope: a specific branch (if allowed) or the caller's scope.
    if payload.branch_id is not None:
        current.assert_branch_access(payload.branch_id)
        branch_ids: list[int] | None = [payload.branch_id]
    else:
        branch_ids = None if current.sees_all_branches else (current.branch_ids or [-1])

    ctx = tools.ToolContext(
        db=db, organization_id=current.organization_id, branch_ids=branch_ids
    )
    result = assistant.ask(ctx, payload.question)
    return AskResponse(**result)
