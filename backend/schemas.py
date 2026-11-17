from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict


class RegisterIn(BaseModel):
    account: str
    password: str
    nickname: str = "同学"
    email: Optional[str] = None
    email_code: Optional[str] = None
    major: str = ""
    role: str = "student"
    captcha_id: str
    captcha_answer: str


class LoginIn(BaseModel):
    account: str
    password: str
    remember: bool = False
    captcha_id: str
    captcha_answer: str


class SendCodeIn(BaseModel):
    email: str


class CodeLoginIn(BaseModel):
    email: str
    code: str
    remember: bool = False


class ChangePasswordIn(BaseModel):
    old_password: str
    new_password: str


class BindEmailIn(BaseModel):
    email: str
    code: str


class PermissionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    code: str
    name: str
    description: str


class RoleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    code: str
    description: str
    is_system: bool
    permissions: List[PermissionOut] = []


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    account: str
    email: Optional[str]
    nickname: str
    major: str
    is_active: bool
    must_change_password: bool
    status: str
    created_at: datetime
    roles: List[RoleOut] = []
    direct_permissions: List[PermissionOut] = []


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut
    permissions: List[str] = []


class UserCreate(BaseModel):
    account: str
    password: str
    nickname: str = "同学"
    email: Optional[str] = None
    major: str = ""
    role_ids: List[int] = []
    permission_ids: List[int] = []


class UserUpdate(BaseModel):
    nickname: Optional[str] = None
    email: Optional[str] = None
    major: Optional[str] = None
    is_active: Optional[bool] = None
    password: Optional[str] = None
    role_ids: Optional[List[int]] = None
    permission_ids: Optional[List[int]] = None


class RoleCreate(BaseModel):
    name: str
    code: str
    description: str = ""
    permission_ids: List[int] = []


class RoleUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    permission_ids: Optional[List[int]] = None
