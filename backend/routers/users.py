from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

import models, schemas, security, mq
from database import get_db
from deps import require_permission

router = APIRouter(prefix="/api/users", tags=["用户管理"])


@router.get("/permissions", response_model=List[schemas.PermissionOut])
def list_permissions(db: Session = Depends(get_db), user=Depends(require_permission("user.manage"))):
    return db.query(models.Permission).order_by(models.Permission.id).all()


@router.get("/", response_model=List[schemas.UserOut])
def list_users(db: Session = Depends(get_db), user=Depends(require_permission("user.manage"))):
    return db.query(models.User).order_by(models.User.id).all()


@router.post("/", response_model=schemas.UserOut)
def create_user(data: schemas.UserCreate, db: Session = Depends(get_db), user=Depends(require_permission("user.manage"))):
    if db.query(models.User).filter(models.User.account == data.account).first():
        raise HTTPException(status_code=400, detail="该学号已存在")
    u = models.User(
        account=data.account, email=data.email,
        password_hash=security.hash_password(data.password),
        nickname=data.nickname, major=data.major,
    )
    for rid in data.role_ids:
        role = db.query(models.Role).get(rid)
        if role:
            u.roles.append(role)
    for pid in data.permission_ids:
        perm = db.query(models.Permission).get(pid)
        if perm:
            u.direct_permissions.append(perm)
    db.add(u)
    db.commit()
    db.refresh(u)
    mq.publish_event("user_create", account=u.account, nickname=u.nickname,
                     detail=f"创建用户 {u.account}", user_id=u.id)
    return u


@router.put("/{user_id}", response_model=schemas.UserOut)
def update_user(user_id: int, data: schemas.UserUpdate, db: Session = Depends(get_db), user=Depends(require_permission("user.manage"))):
    u = db.query(models.User).get(user_id)
    if not u:
        raise HTTPException(status_code=404, detail="用户不存在")
    if data.nickname is not None:
        u.nickname = data.nickname
    if data.email is not None:
        u.email = data.email
    if data.major is not None:
        u.major = data.major
    if data.is_active is not None:
        u.is_active = data.is_active
    if data.password:
        u.password_hash = security.hash_password(data.password)
    if data.role_ids is not None:
        u.roles = [db.query(models.Role).get(rid) for rid in data.role_ids if db.query(models.Role).get(rid)]
    if data.permission_ids is not None:
        u.direct_permissions = [db.query(models.Permission).get(pid) for pid in data.permission_ids if db.query(models.Permission).get(pid)]
    db.commit()
    db.refresh(u)
    mq.publish_event("user_update", account=u.account, nickname=u.nickname,
                     detail=f"更新用户 {u.account}", user_id=u.id)
    return u


@router.delete("/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db), user=Depends(require_permission("user.manage"))):
    u = db.query(models.User).get(user_id)
    if not u:
        raise HTTPException(status_code=404, detail="用户不存在")
    if u.id == user.id:
        raise HTTPException(status_code=400, detail="不能删除当前登录账号")
    account, nickname = u.account, u.nickname
    db.delete(u)
    db.commit()
    mq.publish_event("user_delete", account=account, nickname=nickname,
                     detail=f"删除用户 {account}")
    return {"ok": True}


@router.post("/{user_id}/approve")
def approve_user(user_id: int, db: Session = Depends(get_db), user=Depends(require_permission("user.manage"))):
    u = db.query(models.User).get(user_id)
    if not u:
        raise HTTPException(status_code=404, detail="用户不存在")
    u.status = "active"
    db.commit()
    mq.publish_event("teacher_approve", account=u.account, nickname=u.nickname,
                     detail=f"审核通过 {u.account}", user_id=u.id)
    return {"ok": True, "message": "已通过审核"}


@router.post("/{user_id}/reject")
def reject_user(user_id: int, db: Session = Depends(get_db), user=Depends(require_permission("user.manage"))):
    u = db.query(models.User).get(user_id)
    if not u:
        raise HTTPException(status_code=404, detail="用户不存在")
    u.status = "rejected"
    db.commit()
    mq.publish_event("teacher_reject", account=u.account, nickname=u.nickname,
                     detail=f"审核拒绝 {u.account}", user_id=u.id)
    return {"ok": True, "message": "已拒绝"}
