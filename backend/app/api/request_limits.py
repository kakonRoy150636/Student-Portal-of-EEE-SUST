from fastapi import Depends, Request

from app.api.dependencies import get_client_ip, get_current_user
from app.core.request_limits import enforce_request_limit
from app.models.user import User


async def limit_login(request: Request):
    await enforce_request_limit("login", get_client_ip(request), 30)


async def limit_refresh(request: Request):
    await enforce_request_limit("refresh", get_client_ip(request), 60)


async def limit_registration(request: Request):
    await enforce_request_limit("registration", get_client_ip(request), 20, 3600)


async def limit_ai(user: User = Depends(get_current_user)):
    await enforce_request_limit("ai", str(user.id), 10)


async def limit_search(user: User = Depends(get_current_user)):
    await enforce_request_limit("resource-search", str(user.id), 60)
