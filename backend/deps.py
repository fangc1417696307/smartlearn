from typing import Optional, Set
import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

import models
from database import get_db
from security import decode_token

bearer = HTTPBearer(auto_error=False)


def token_user(db: Session, token: str) -> Optional[models.User]:
    """按 token 解析有效用户；无效 / 过期 / 停用一律返回 None。

    HTTP 与 WebSocket 共用：WS 握手时没有 Authorization 头，token 放在 query 里。
    """
    if not token:
        return None
    try:
        payload = decode_token(token)
        user_id = int(payload["sub"])
    except Exception:  # noqa: BLE001 - 过期或伪造 token
        return None
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user or not user.is_active or user.status != "active":
        return None
    return user


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
    db: Session = Depends(get_db),
) -> models.User:
    if not credentials:
        raise HTTPException(status_code=401, detail="未登录")
    try:
        payload = decode_token(credentials.credentials)
        user_id = int(payload["sub"])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="登录已过期，请重新登录")
    except Exception:
        raise HTTPException(status_code=401, detail="无效的登录凭证")
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="用户不存在")
    return user


def get_permissions(user: models.User, db: Session) -> Set[str]:
    perms: Set[str] = set()
    for role in user.roles:
        for p in role.permissions:
            perms.add(p.code)
    # 用户被单独授予的权限（与角色权限取并集）
    for p in user.direct_permissions:
        perms.add(p.code)
    return perms


def require_permission(code: str):
    def checker(user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
        if code not in get_permissions(user, db):
            raise HTTPException(status_code=403, detail=f"无权限：{code}")
        return user
    return checker
