import time
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

import models, schemas, security, verifications, mq
from database import get_db
from deps import get_current_user, get_permissions
from email_sender import send_email_code

router = APIRouter(prefix="/api/auth", tags=["认证"])

_send_cooldown = {}  # email -> timestamp


def _check_arith(captcha_id: str, captcha_answer: str):
    if not verifications.verify_arithmetic(captcha_id, captcha_answer):
        raise HTTPException(status_code=400, detail="验证码错误或已过期")


def _token_response(user, db, remember=False):
    token = security.create_token(user.id, remember=remember)
    return {"access_token": token, "user": user, "permissions": sorted(get_permissions(user, db))}


@router.get("/captcha")
def get_captcha():
    """生成算数验证码"""
    return verifications.generate_arithmetic()


@router.post("/register")
def register(data: schemas.RegisterIn, db: Session = Depends(get_db)):
    _check_arith(data.captcha_id, data.captcha_answer)
    if db.query(models.User).filter(models.User.account == data.account).first():
        raise HTTPException(status_code=400, detail="该学号已注册")
    if data.email:
        if db.query(models.User).filter(models.User.email == data.email).first():
            raise HTTPException(status_code=400, detail="该邮箱已被使用")
        if not data.email_code or not verifications.verify_email_code(data.email, data.email_code):
            raise HTTPException(status_code=400, detail="邮箱验证码错误或已过期")
    role_code = data.role if data.role in ("student", "teacher") else "student"
    user = models.User(
        account=data.account,
        email=data.email,
        password_hash=security.hash_password(data.password),
        nickname=data.nickname,
        major=data.major,
        status="active" if role_code == "student" else "pending",
    )
    role = db.query(models.Role).filter(models.Role.code == role_code).first()
    if role:
        user.roles.append(role)
    db.add(user)
    db.commit()
    db.refresh(user)
    mq.publish_event(
        "register",
        account=user.account,
        nickname=user.nickname,
        detail="教师注册（待审核）" if role_code == "teacher" else "学生注册",
        user_id=user.id,
    )
    if role_code == "teacher":
        return {"pending": True, "message": "注册成功，请等待管理员审核"}
    return _token_response(user, db)


@router.post("/login", response_model=schemas.TokenOut)
def login(data: schemas.LoginIn, db: Session = Depends(get_db)):
    _check_arith(data.captcha_id, data.captcha_answer)
    user = db.query(models.User).filter(
        (models.User.account == data.account) | (models.User.email == data.account)
    ).first()
    if not user or not security.verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=400, detail="账号或密码错误")
    if user.status == "pending":
        raise HTTPException(status_code=403, detail="账号正在等待管理员审核，请耐心等待")
    if user.status == "rejected":
        raise HTTPException(status_code=403, detail="注册申请已被拒绝")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="该账号已被禁用")
    mq.publish_event(
        "login",
        account=user.account,
        nickname=user.nickname,
        detail="密码登录",
        user_id=user.id,
    )
    return _token_response(user, db, remember=data.remember)


@router.post("/send-code")
def send_code(data: schemas.SendCodeIn, db: Session = Depends(get_db)):
    email = data.email
    if time.time() - _send_cooldown.get(email, 0) < 60:
        raise HTTPException(status_code=429, detail="发送过于频繁，请 60 秒后再试")
    code = verifications.generate_email_code(email)
    _send_cooldown[email] = time.time()
    if not send_email_code(email, code):
        raise HTTPException(status_code=500, detail="验证码发送失败，请检查邮箱配置")
    return {"ok": True, "message": "验证码已发送"}


@router.post("/code-login", response_model=schemas.TokenOut)
def code_login(data: schemas.CodeLoginIn, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == data.email).first()
    if not user:
        raise HTTPException(status_code=400, detail="该邮箱未绑定任何账号")
    if not verifications.verify_email_code(data.email, data.code):
        raise HTTPException(status_code=400, detail="验证码错误或已过期")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="该账号已被禁用")
    mq.publish_event(
        "login",
        account=user.account,
        nickname=user.nickname,
        detail="邮箱验证码登录",
        user_id=user.id,
    )
    return _token_response(user, db, remember=data.remember)


@router.post("/change-password")
def change_password(data: schemas.ChangePasswordIn, user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not security.verify_password(data.old_password, user.password_hash):
        raise HTTPException(status_code=400, detail="原密码错误")
    if len(data.new_password) < 6:
        raise HTTPException(status_code=400, detail="新密码至少 6 位")
    user.password_hash = security.hash_password(data.new_password)
    user.must_change_password = False
    db.commit()
    return {"ok": True, "message": "密码已修改"}


@router.post("/bind-email")
def bind_email(data: schemas.BindEmailIn, user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not verifications.verify_email_code(data.email, data.code):
        raise HTTPException(status_code=400, detail="验证码错误或已过期")
    if db.query(models.User).filter(models.User.email == data.email, models.User.id != user.id).first():
        raise HTTPException(status_code=400, detail="该邮箱已被其他账号绑定")
    user.email = data.email
    db.commit()
    return {"ok": True, "message": "邮箱绑定成功"}


@router.post("/unbind-email")
def unbind_email(user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    """解绑当前账号的邮箱（解绑后不能再使用邮箱验证码登录）"""
    if not user.email:
        raise HTTPException(status_code=400, detail="当前账号未绑定邮箱")
    user.email = None
    db.commit()
    return {"ok": True, "message": "邮箱已解绑"}


@router.get("/me", response_model=schemas.UserOut)
def me(user: models.User = Depends(get_current_user)):
    return user
