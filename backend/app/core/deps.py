"""Shared FastAPI dependencies: current user, permission and branch-scope guards."""
from __future__ import annotations

from dataclasses import dataclass, field

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core import rbac
from app.core.database import get_db
from app.core.security import decode_token
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/login", auto_error=False)


@dataclass
class CurrentUser:
    user: User
    role_key: str
    branch_ids: list[int] = field(default_factory=list)

    @property
    def id(self) -> int:
        return self.user.id

    @property
    def organization_id(self) -> int:
        return self.user.organization_id

    def has_permission(self, permission: str) -> bool:
        return rbac.role_has_permission(self.role_key, permission)

    @property
    def sees_all_branches(self) -> bool:
        return rbac.sees_all_branches(self.role_key)

    def assert_branch_access(self, branch_id: int) -> None:
        if self.sees_all_branches:
            return
        if branch_id not in self.branch_ids:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No access to this branch",
            )


def get_current_user(
    token: str | None = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> CurrentUser:
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            raise HTTPException(status_code=401, detail="Invalid token type")
        user_id = int(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        raise HTTPException(status_code=401, detail="Could not validate credentials")

    user = db.get(User, user_id)
    if user is None or not user.is_active or user.is_deleted:
        raise HTTPException(status_code=401, detail="User not found or inactive")

    branch_ids = [b.id for b in user.branches]
    return CurrentUser(user=user, role_key=user.role.key, branch_ids=branch_ids)


def require_permission(permission: str):
    """Dependency factory enforcing a role permission."""

    def _guard(current: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if not current.has_permission(permission):
            raise HTTPException(status_code=403, detail=f"Missing permission: {permission}")
        return current

    return _guard
