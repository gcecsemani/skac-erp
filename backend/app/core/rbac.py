"""Role definitions and permission catalogue.

Only two roles are used:
- owner: full access across every branch
- cashier: POS, invoices, sales returns, farmers, expenses, day close, and field visits for assigned branch(es)
"""
from __future__ import annotations

ROLE_OWNER = "owner"
ROLE_CASHIER = "cashier"

DEFAULT_ROLES: list[dict] = [
    {"key": ROLE_OWNER, "name": "Owner", "description": "Full access, all branches"},
    {"key": ROLE_CASHIER, "name": "Cashier", "description": "POS, invoices, returns, farmers, expenses, day close and field visits for assigned branch"},
]

ALLOWED_ROLE_KEYS = {ROLE_OWNER, ROLE_CASHIER}

# Permission strings
P_BRANCH_MANAGE = "branch:manage"
P_USER_MANAGE = "user:manage"
P_PRODUCT_MANAGE = "product:manage"
P_PRODUCT_EDIT_PRICE = "product:edit_price"
P_INVENTORY_MANAGE = "inventory:manage"
P_CUSTOMER_MANAGE = "customer:manage"
P_SALE_CREATE = "sale:create"
P_SALE_CANCEL = "sale:cancel"
P_PURCHASE_MANAGE = "purchase:manage"
P_ACCOUNTING_VIEW = "accounting:view"
P_ACCOUNTING_MANAGE = "accounting:manage"
P_EXPENSE_MANAGE = "expense:manage"
P_REPORT_VIEW = "report:view"
P_AI_USE = "ai:use"
P_AUDIT_VIEW = "audit:view"
P_CONFIG_MANAGE = "config:manage"
P_FIELD_VISIT = "field_visit:manage"

_ALL = {
    P_BRANCH_MANAGE, P_USER_MANAGE, P_PRODUCT_MANAGE, P_PRODUCT_EDIT_PRICE,
    P_INVENTORY_MANAGE, P_CUSTOMER_MANAGE, P_SALE_CREATE, P_SALE_CANCEL,
    P_PURCHASE_MANAGE, P_ACCOUNTING_VIEW, P_ACCOUNTING_MANAGE, P_EXPENSE_MANAGE,
    P_REPORT_VIEW, P_AI_USE, P_AUDIT_VIEW, P_CONFIG_MANAGE, P_FIELD_VISIT,
}

ROLE_PERMISSIONS: dict[str, set[str]] = {
    ROLE_OWNER: set(_ALL),
    ROLE_CASHIER: {
        P_SALE_CREATE,
        P_SALE_CANCEL,
        P_CUSTOMER_MANAGE,
        P_EXPENSE_MANAGE,
        P_FIELD_VISIT,
    },
}

REQUIRE_2FA_ROLES = {ROLE_OWNER}


def role_has_permission(role_key: str, permission: str) -> bool:
    return permission in ROLE_PERMISSIONS.get(role_key, set())


def sees_all_branches(role_key: str) -> bool:
    return role_key == ROLE_OWNER
