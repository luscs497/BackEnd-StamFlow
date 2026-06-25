from fastapi import APIRouter
from app.api.routes import (auth, tickets, reports, companies, managers, subscriptions, subscription_plans, webhooks, invites, account, enterprise, notifications)

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(tickets.router, prefix="/tickets", tags=["tickets"])
api_router.include_router(reports.router, prefix="/reports", tags=["reports"])
api_router.include_router(companies.router, prefix="/company", tags=["companies"])
api_router.include_router(managers.router, prefix="/manager", tags=["managers"])
api_router.include_router(subscriptions.router, prefix="/subscription", tags=["subscriptions"])
api_router.include_router(subscription_plans.router, prefix="/subscription_plan", tags=["subscription_plans"])
api_router.include_router(webhooks.router, prefix="/webhook", tags=["webhooks"])
api_router.include_router(invites.router, prefix="/invite", tags=["invites"])
api_router.include_router(account.router, prefix="/account", tags=["account"])
api_router.include_router(enterprise.router, prefix="/enterprise", tags=["enterprise"])
api_router.include_router(notifications.router, prefix="/notifications", tags=["notifications"])