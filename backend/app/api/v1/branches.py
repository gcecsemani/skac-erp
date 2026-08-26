"""Branch master management (central admin console)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import rbac
from app.core.audit import record_audit
from app.core.database import get_db
from app.core.deps import CurrentUser, get_current_user, require_permission
from app.models.organization import Branch
from app.models.sales import Invoice
from app.schemas.masters import BranchCreate, BranchOut

router = APIRouter(prefix="/branches", tags=["branches"])


@router.get("", response_model=list[BranchOut])
def list_branches(
    current: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[Branch]:
    stmt = select(Branch).where(
        Branch.organization_id == current.organization_id, Branch.is_deleted.is_(False)
    )
    if not current.sees_all_branches:
        stmt = stmt.where(Branch.id.in_(current.branch_ids or [-1]))
    return list(db.scalars(stmt).all())


@router.post("", response_model=BranchOut, status_code=201)
def create_branch(
    payload: BranchCreate,
    current: CurrentUser = Depends(require_permission(rbac.P_BRANCH_MANAGE)),
    db: Session = Depends(get_db),
) -> Branch:
    if payload.thermal_paper_mm not in (58, 80):
        raise HTTPException(status_code=400, detail="thermal_paper_mm must be 58 or 80")
    branch = Branch(organization_id=current.organization_id, **payload.model_dump())
    db.add(branch)
    db.flush()
    record_audit(
        db, action="create", entity_type="branch", entity_id=branch.id,
        actor_user_id=current.id, organization_id=current.organization_id,
        branch_id=branch.id, changes=payload.model_dump(mode="json"),
    )
    db.commit()
    db.refresh(branch)
    return branch


def _owned_branch(db: Session, branch_id: int, org_id: int) -> Branch:
    branch = db.get(Branch, branch_id)
    if branch is None or branch.organization_id != org_id or branch.is_deleted:
        raise HTTPException(status_code=404, detail="Branch not found")
    return branch


@router.put("/{branch_id}", response_model=BranchOut)
def update_branch(
    branch_id: int,
    payload: BranchCreate,
    current: CurrentUser = Depends(require_permission(rbac.P_BRANCH_MANAGE)),
    db: Session = Depends(get_db),
) -> Branch:
    branch = _owned_branch(db, branch_id, current.organization_id)
    if payload.thermal_paper_mm not in (58, 80):
        raise HTTPException(status_code=400, detail="thermal_paper_mm must be 58 or 80")
    for key, value in payload.model_dump().items():
        setattr(branch, key, value)
    record_audit(
        db, action="update", entity_type="branch", entity_id=branch.id,
        actor_user_id=current.id, organization_id=current.organization_id,
        branch_id=branch.id, changes=payload.model_dump(mode="json"),
    )
    db.commit()
    db.refresh(branch)
    return branch


@router.delete("/{branch_id}")
def delete_branch(
    branch_id: int,
    current: CurrentUser = Depends(require_permission(rbac.P_BRANCH_MANAGE)),
    db: Session = Depends(get_db),
) -> dict:
    branch = _owned_branch(db, branch_id, current.organization_id)
    remaining = db.scalar(
        select(Branch).where(
            Branch.organization_id == current.organization_id,
            Branch.is_deleted.is_(False),
            Branch.id != branch_id,
        )
    )
    if remaining is None:
        raise HTTPException(status_code=409, detail="Cannot delete the last branch")
    has_invoices = db.scalar(
        select(Invoice.id).where(Invoice.branch_id == branch_id).limit(1)
    )
    if has_invoices is not None:
        raise HTTPException(
            status_code=409,
            detail="This branch has invoices. Deactivate is not allowed — keep it for GST history.",
        )
    branch.is_deleted = True
    record_audit(
        db, action="delete", entity_type="branch", entity_id=branch.id,
        actor_user_id=current.id, organization_id=current.organization_id,
        branch_id=branch.id,
    )
    db.commit()
    return {"status": "deleted", "id": branch_id}
