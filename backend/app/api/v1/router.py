"""Aggregate all v1 routers."""
from fastapi import APIRouter

from app.api.v1 import (
    accounting,
    admin,
    ai,
    auth,
    branches,
    config,
    customers,
    expenses,
    inventory,
    products,
    purchasing,
    reports,
    returns,
    sales,
    transfers,
)

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(branches.router)
api_router.include_router(config.router)
api_router.include_router(products.router)
api_router.include_router(customers.router)
api_router.include_router(inventory.router)
api_router.include_router(sales.router)
api_router.include_router(returns.router)
api_router.include_router(purchasing.router)
api_router.include_router(transfers.router)
api_router.include_router(accounting.router)
api_router.include_router(expenses.router)
api_router.include_router(reports.router)
api_router.include_router(admin.router)
api_router.include_router(ai.router)
