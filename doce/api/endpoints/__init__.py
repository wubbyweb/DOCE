from fastapi import APIRouter

from .auth import router as auth_router
from .users import router as users_router
from .contracts import router as contracts_router
from .invoices import router as invoices_router
from .workflow_rules import router as workflow_rules_router

api_router = APIRouter()

api_router.include_router(auth_router, prefix="/auth", tags=["authentication"])
api_router.include_router(users_router, prefix="/users", tags=["users"])
api_router.include_router(contracts_router, prefix="/contracts", tags=["contracts"])
api_router.include_router(invoices_router, prefix="/invoices", tags=["invoices"])
api_router.include_router(workflow_rules_router, prefix="/workflow-rules", tags=["workflow rules"])