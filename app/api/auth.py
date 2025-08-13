from fastapi import APIRouter, HTTPException, Depends
from jwt import PyJWTError

from core.error_handle import AuthorizationException
from core.i18n import _
from core.extends_logger import logger
from core.middleware import login_required
from schemas.result import ok, failed
from schemas.user import UserCreate, UserLogin, UserSecuritySetting
from services.user_service import UserService
from core.error_handle import AuthorizationException

router = APIRouter()

def get_user_service():
    return UserService()

@router.post("/register")
async def register(user: UserCreate, user_service: UserService = Depends(get_user_service)):
    user = await user_service.register_user(user)
    return ok(user.to_dict(filter=["id","username", "email", "mobile", "create_time", "update_time"]))

@router.post("/login")
async def login(user: UserLogin, user_service: UserService = Depends(get_user_service)):
    result = await user_service.login_user(user)
    return ok(result)


@router.post("/logout")
async def logout():
    return ok(None)

@router.post("/info")
async def user_info(user: dict = Depends(login_required), user_service: UserService = Depends(get_user_service)):
    try:
        userid = user.get('userid')
        if userid:
            user = await user_service.find_by_id(userid)
            if user:
                return ok(user.to_dict(filter=["id","username", "email", "mobile", "role","create_time", "update_time"]))
    except Exception as e:
        raise AuthorizationException(code=AuthorizationException.UNAUTHORIZED, msg=str(e))

    raise AuthorizationException(code=AuthorizationException.USERID_NOT_FOUND_IN_TOKEN, msg=_("Userid not found in token"))


@router.put("/update")
async def update_user_info(data: UserCreate, user: dict = Depends(login_required), user_service: UserService = Depends(get_user_service)):
    userid = user.get('userid')
    if not userid == data.id:
        raise AuthorizationException(code=AuthorizationException.UNAUTHORIZED, msg=_("Unauthorized"))
    try:
        user = await user_service.save_user(data)
        if user:
            return ok(user.to_dict(filter=["id","username", "email", "mobile", "role","create_time", "update_time"]))
    except HTTPException as e:
        return failed(data=None, msg=e.detail)
    except Exception as e:
        print("update_user_info error", e)
        logger.error(f"update_user_info error: {e}")
        return failed(data=None, msg=str(e))

@router.put("/update/password")
async def update_password(data: UserSecuritySetting, user: dict = Depends(login_required), user_service: UserService = Depends(get_user_service)):
    try:
        userid = user.get('userid')
        user = await user_service.update_user_password(userid, data)
        if user:
            return ok(user.to_dict(filter=["id","username", "email", "mobile", "role","create_time", "update_time"]))
    except HTTPException as e:
        return failed(data=None, msg=e.detail)
    except Exception as e:
        logger.error(f"update_user_info error: {e}")
        return failed(data=None, msg=str(e))