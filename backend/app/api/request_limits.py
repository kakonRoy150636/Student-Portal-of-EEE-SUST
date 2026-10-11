from fastapi import Depends, Request

from app.api.dependencies import get_avatar_actor, get_client_ip, get_current_user
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


async def limit_alumni_search(user: User = Depends(get_current_user)):
    await enforce_request_limit("alumni-search", str(user.id), 60)


async def limit_resource_upload(request: Request, user: User = Depends(get_current_user)):
    """Bound presign/finalize calls that can consume object-store capacity."""
    await enforce_request_limit("resource-upload-user", str(user.id), 20, 3600)
    await enforce_request_limit("resource-upload-ip", get_client_ip(request), 60, 3600)


async def limit_avatar_upload(request: Request, user: User = Depends(get_avatar_actor)):
    """Bound avatar staging URLs and post-upload validation work."""
    await enforce_request_limit("avatar-upload-user", str(user.id), 10, 3600)
    await enforce_request_limit("avatar-upload-ip", get_client_ip(request), 30, 3600)
