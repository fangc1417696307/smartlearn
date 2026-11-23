from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, Table, ForeignKey, UniqueConstraint,
)
from sqlalchemy.orm import relationship
from database import Base

user_roles = Table(
    "user_roles", Base.metadata,
    Column("user_id", Integer, ForeignKey("users.id"), primary_key=True),
    Column("role_id", Integer, ForeignKey("roles.id"), primary_key=True),
)

role_permissions = Table(
    "role_permissions", Base.metadata,
    Column("role_id", Integer, ForeignKey("roles.id"), primary_key=True),
    Column("permission_id", Integer, ForeignKey("permissions.id"), primary_key=True),
)

user_permissions = Table(
    "user_permissions", Base.metadata,
    Column("user_id", Integer, ForeignKey("users.id"), primary_key=True),
    Column("permission_id", Integer, ForeignKey("permissions.id"), primary_key=True),
)


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    account = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, nullable=True)
    password_hash = Column(String, nullable=False)
    nickname = Column(String, default="同学")
    major = Column(String, default="")
    is_active = Column(Boolean, default=True)
    must_change_password = Column(Boolean, default=False)
    status = Column(String, default="active")
    created_at = Column(DateTime, default=datetime.utcnow)
    roles = relationship("Role", secondary=user_roles, back_populates="users")
    direct_permissions = relationship("Permission", secondary=user_permissions)


class Role(Base):
    __tablename__ = "roles"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    code = Column(String, unique=True, nullable=False)
    description = Column(String, default="")
    is_system = Column(Boolean, default=False)
    users = relationship("User", secondary=user_roles, back_populates="roles")
    permissions = relationship("Permission", secondary=role_permissions, back_populates="roles")


class Permission(Base):
    __tablename__ = "permissions"
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=False)
    description = Column(String, default="")
    roles = relationship("Role", secondary=role_permissions, back_populates="permissions")


# ---------------------------------------------------------------------------
# 即时聊天（对应 PPT：一条消息的一生 / 顺序性 / 离线同步 / 在线状态）
# ---------------------------------------------------------------------------

class Conversation(Base):
    """会话：私聊（private）或群聊（group）。"""
    __tablename__ = "conversations"
    id = Column(Integer, primary_key=True, index=True)
    type = Column(String, nullable=False, default="private")  # private | group
    name = Column(String, default="")                          # 群聊名称，私聊为空
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    members = relationship(
        "ConversationMember", back_populates="conversation", cascade="all, delete-orphan"
    )


class ConversationMember(Base):
    """会话成员。last_read_seq 就是 PPT P12 的已读游标，未读数 = 最新 seq - 该值。"""
    __tablename__ = "conversation_members"
    conv_id = Column(
        Integer, ForeignKey("conversations.id", ondelete="CASCADE"), primary_key=True
    )
    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    joined_at = Column(DateTime, default=datetime.utcnow)
    last_read_seq = Column(Integer, nullable=False, default=0)
    conversation = relationship("Conversation", back_populates="members")
    user = relationship("User")


class Message(Base):
    """消息表。

    - (conv_id, seq) 唯一：保证会话内顺序，防并发发号重号（PPT P11）
    - client_id 唯一：客户端幂等去重的锚点（PPT P10）
    """
    __tablename__ = "messages"
    __table_args__ = (
        UniqueConstraint("conv_id", "seq", name="uq_messages_conv_seq"),
    )
    id = Column(Integer, primary_key=True, index=True)
    conv_id = Column(Integer, ForeignKey("conversations.id"), nullable=False, index=True)
    seq = Column(Integer, nullable=False)
    sender_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    client_id = Column(String, nullable=False, unique=True, index=True)
    body = Column(String, nullable=False)
    msg_type = Column(String, default="text")
    created_at = Column(DateTime, default=datetime.utcnow)
