from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

import models, schemas
from database import get_db
from deps import require_permission

router = APIRouter(prefix="/api/students", tags=["学生查看"])


@router.get("/", response_model=List[schemas.UserOut])
def list_students(db: Session = Depends(get_db), user=Depends(require_permission("student.view"))):
    """老师/管理员查看学生列表"""
    return (
        db.query(models.User)
        .join(models.user_roles)
        .join(models.Role)
        .filter(models.Role.code == "student", models.User.status == "active")
        .order_by(models.User.id)
        .all()
    )
