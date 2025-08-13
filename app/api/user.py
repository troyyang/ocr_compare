from fastapi import APIRouter, HTTPException, Depends

from core.error_handle import AuthorizationException
from core.extends_logger import logger
from core.i18n import _
from core.middleware import login_required
from models.models import UserRole
from schemas.result import ok, failed
from schemas.user import UserCreate, UserList
from services.user_service import UserService
from core.error_handle import AuthorizationException, MyException

router = APIRouter()

def get_user_service():
    return UserService()

@router.post("/list")
async def user_list(condition: UserList, user: dict = Depends(login_required), user_service: UserService = Depends(get_user_service)):
    try:
        userid = user.get('userid')
        if userid:
            user = user_service.find_by_id(userid)
            if not user or not user.role == UserRole.admin:
                raise AuthorizationException(code=AuthorizationException.UNAUTHORIZED, msg=_("Unauthorized"))

            users, total = user_service.find(condition)
            return ok({
                        "total": total,
                        "list": [user.to_dict(filter=["id","username", "email", "mobile", "role","create_time", "update_time"]) for user in users]})
    except MyException as e:
        return failed(data=None, msg=e.msg)
    except Exception as e:
        logger.error(f"user_list error: {e}")
        return failed(data=None, msg=str(e))


@router.put("")
async def user_save(data: UserCreate, user: dict = Depends(login_required), user_service: UserService = Depends(get_user_service)):
    try:
        userid = user.get('userid')
        if userid:
            user = user_service.find_by_id(userid)
            if not user or not user.role == UserRole.admin:
                raise AuthorizationException(code=AuthorizationException.UNAUTHORIZED, msg=_("Unauthorized"))
            user = user_service.save_user(data)
            return ok(user.to_dict(filter=["id","username", "email", "mobile", "role","create_time", "update_time"]))
    except MyException as e:
        return failed(data=None, msg=e.msg)
    except Exception as e:
        logger.error(f"user_save error: {e}")
        return failed(data=None, msg=str(e))


@router.delete("/{user_id}")
async def user_delete(user_id: int, user: dict = Depends(login_required), user_service: UserService = Depends(get_user_service)):
    try:
        userid = user.get('userid')
        if userid:
            user = user_service.find_by_id(userid)
            if not user or not user.role == UserRole.admin:
                raise AuthorizationException(code=AuthorizationException.UNAUTHORIZED, msg=_("Unauthorized"))

            user_service.delete_user(user_id)
            return ok({"success": True})
    except MyException as e:
        return failed(data=None, msg=e.msg)
    except Exception as e:
        logger.error(f"user_delete error: {e}")
        return failed(data=None, msg=str(e))

@router.get("/department/tree")
async def department_tree(user: dict = Depends(login_required), user_service: UserService = Depends(get_user_service)):
    try:
        access_token = user.get("token")
        data = user_service.department_tree(access_token)
        if data.get("status") != 0:
            raise MyException(code=data.get("status"), msg=data.get("msg"))
        return ok(data.get("data"))
    except MyException as e:
        return failed(data=None, msg=e.msg)
    except Exception as e:
        logger.error(f"department_tree error: {e}")
        return failed(data=None, msg=str(e))

@router.get("/department/staffs/{department_id}")
async def staffs_by_department_id(department_id: str, user: dict = Depends(login_required), user_service: UserService = Depends(get_user_service)):
    try:
        access_token = user.get("token")
        data = user_service.staffs_by_department_id(department_id, access_token)
        if data.get("status") != 0:
            raise MyException(code=data.get("status"), msg=data.get("msg"))
        return ok(data.get("data"))
    except MyException as e:
        return failed(data=None, msg=e.msg)
    except Exception as e:
        logger.error(f"staffs_by_department_id error: {e}")
        return failed(data=None, msg=str(e))
