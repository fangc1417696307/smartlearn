from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

import models, schemas
from database import get_db
from deps import require_permission

router = APIRouter(prefix="/api/roles", tags=["角色管理"])


@router.get("/permissions", response_model=List[schemas.PermissionOut])
def list_permissions(db: Session = Depends(get_db), user=Depends(require_permission("role.manage"))):
    return db.query(models.Permission).order_by(models.Permission.id).all()


@router.get("/", response_model=List[schemas.RoleOut])
def list_roles(db: Session = Depends(get_db), user=Depends(require_permission("role.manage"))):
    return db.query(models.Role).order_by(models.Role.id).all()


@router.post("/", response_model=schemas.RoleOut)
def create_role(data: schemas.RoleCreate, db: Session = Depends(get_db), user=Depends(require_permission("role.manage"))):
    if db.query(models.Role).filter(models.Role.code == data.code).first():
        raise HTTPException(status_code=400, detail="角色编码已存在")
    role = models.Role(name=data.name, code=data.code, description=data.description, is_system=False)
    role.permissions = [db.query(models.Permission).get(pid) for pid in data.permission_ids if db.query(models.Permission).get(pid)]
    db.add(role)
    db.commit()
    db.refresh(role)
    return role


@router.put("/{role_id}", response_model=schemas.RoleOut)
def update_role(role_id: int, data: schemas.RoleUpdate, db: Session = Depends(get_db), user=Depends(require_permission("role.manage"))):
    role = db.query(models.Role).get(role_id)
    if not role:
        raise HTTPException(status_code=404, detail="角色不存在")
    if data.name is not None:
        role.name = data.name
    if data.description is not None:
        role.description = data.description
    if data.permission_ids is not None:
        role.permissions = [db.query(models.Permission).get(pid) for pid in data.permission_ids if db.query(models.Permission).get(pid)]
    db.commit()
    db.refresh(role)
    return role


@router.delete("/{role_id}")
def delete_role(role_id: int, db: Session = Depends(get_db), user=Depends(require_permission("role.manage"))):
    role = db.query(models.Role).get(role_id)
    if not role:
        raise HTTPException(status_code=404, detail="角色不存在")
    if role.is_system:
        raise HTTPException(status_code=400, detail="系统内置角色不可删除")
    if role.users:
        raise HTTPException(status_code=400, detail="该角色下仍有用户，无法删除")
    db.delete(role)
    db.commit()
    return {"ok": True}
