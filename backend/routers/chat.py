"""即时聊天：REST（会话/历史/已读）+ WebSocket 网关。

覆盖 PPT 的核心机制：
- P06 WebSocket 最小收发：/ws/chat
- P07 心跳：客户端 ping，服务端 pong；服务端 120s 无消息兜底断开
- P10 可靠送达：clientId 唯一约束去重，重复消息只补 ack 不重投
- P11 顺序性：Redis INCR 分配会话级 seq，(conv_id, seq) 唯一兜底
- P12 离线同步：消息先落库，客户端带 afterSeq 游标拉取
- P13 在线状态：chat_hub 写 Redis online 表，心跳续期，多端并存
- P16 安全：握手验 JWT + 每条消息再校验会话成员

注意：本文件的路由处理函数是 async，而项目使用同步 SQLAlchemy，
所有数据库操作都通过 run_in_threadpool 执行，避免阻塞 WebSocket 事件循环。
"""
import asyncio
import json
import time
from collections import deque
from typing import List, Optional

from fastapi import (
    APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect,
)
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

import chat_hub
import config
import database
import models
import mq
import redis_client
from database import get_db
from deps import get_permissions, require_permission, token_user

router = APIRouter(tags=["即时聊天"])

# 同步 SQLAlchemy 跑在线程池里，每个操作一个短会话
def _with_db(fn):
    db = database.SessionLocal()
    try:
        return fn(db)
    finally:
        db.close()


async def _db(fn):
    return await run_in_threadpool(_with_db, fn)


class ChatError(Exception):
    def __init__(self, code: str, message: str = ""):
        super().__init__(message or code)
        self.code = code
        self.message = message or code


# ---------------------------------------------------------------------------
# 序列化
# ---------------------------------------------------------------------------

def _iso(dt):
    return dt.replace(microsecond=0).isoformat() + "Z" if dt else None


def _user_brief(user) -> dict:
    return {
        "id": user.id,
        "account": user.account,
        "nickname": user.nickname or user.account,
    }


def _me_brief(me: dict) -> dict:
    return {"id": me["id"], "account": me["account"], "nickname": me["nickname"]}


def _msg_out(msg: models.Message, sender: dict) -> dict:
    return {
        "id": msg.id,
        "convId": msg.conv_id,
        "seq": msg.seq,
        "sender": sender,
        "body": msg.body,
        "msgType": msg.msg_type,
        "clientId": msg.client_id,
        "createdAt": _iso(msg.created_at),
    }


def _conversation_out(db: Session, conv: models.Conversation, uid: int) -> Optional[dict]:
    mine = next((m for m in conv.members if m.user_id == uid), None)
    if mine is None:
        return None
    peer = None
    online = None
    if conv.type == "private":
        other = next((m for m in conv.members if m.user_id != uid), None)
        if other and other.user:
            peer = _user_brief(other.user)
            online = chat_hub.is_online(other.user.id)

    last = (
        db.query(models.Message)
        .filter(models.Message.conv_id == conv.id)
        .order_by(models.Message.seq.desc())
        .first()
    )
    last_sender = db.get(models.User, last.sender_id) if last else None
    last_seq = last.seq if last else 0

    return {
        "id": conv.id,
        "type": conv.type,
        "name": conv.name or (peer["nickname"] if peer else "会话"),
        "peer": peer,
        "online": online,
        "memberCount": len(conv.members),
        "ownerId": conv.owner_id,
        "lastSeq": last_seq,
        "unread": max(0, last_seq - (mine.last_read_seq or 0)) if last else 0,
        "lastMessage": _msg_out(last, _user_brief(last_sender)) if last and last_sender else None,
        "updatedAt": _iso(last.created_at if last else conv.created_at),
    }


def _member_ids(db: Session, conv_id: int) -> List[int]:
    rows = (
        db.query(models.ConversationMember.user_id)
        .filter(models.ConversationMember.conv_id == conv_id)
        .all()
    )
    return [r[0] for r in rows]


def _peer_ids(db: Session, uid: int) -> List[int]:
    conv_ids = [
        r[0]
        for r in db.query(models.ConversationMember.conv_id)
        .filter(models.ConversationMember.user_id == uid)
        .all()
    ]
    if not conv_ids:
        return []
    rows = (
        db.query(models.ConversationMember.user_id)
        .filter(
            models.ConversationMember.conv_id.in_(conv_ids),
            models.ConversationMember.user_id != uid,
        )
        .distinct()
        .all()
    )
    return [r[0] for r in rows]


# ---------------------------------------------------------------------------
# 发号：Redis INCR 为主（P11），Redis 不可用时退回 DB 最大值 +1，
# 最终由 (conv_id, seq) 唯一索引兜底
# ---------------------------------------------------------------------------

_SEQ_LUA = """
local cur = redis.call('GET', KEYS[1])
local floor = tonumber(ARGV[1])
if (not cur) or tonumber(cur) < floor then
  redis.call('SET', KEYS[1], floor)
end
return redis.call('INCR', KEYS[1])
"""


def _allocate_seq(conv_id: int, db_max: int) -> int:
    key = config.CHAT_SEQ_KEY.format(conv_id=conv_id)
    seq = redis_client.run(lambda c: int(c.eval(_SEQ_LUA, 1, key, db_max)))
    return seq if seq is not None else db_max + 1


# ---------------------------------------------------------------------------
# 持久化
# ---------------------------------------------------------------------------

def _persist_message(db: Session, me: dict, conv_id: int, client_id: str, body: str):
    """落库并返回 (消息, 是否重复, 成员列表)。重复消息只返回原消息，不重复投递。"""
    conv = db.get(models.Conversation, conv_id)
    if conv is None:
        raise ChatError("NOT_FOUND", "会话不存在")
    member = db.get(models.ConversationMember, (conv_id, me["id"]))
    if member is None:
        raise ChatError("NOT_MEMBER", "你不在该会话中")

    existing = db.query(models.Message).filter(models.Message.client_id == client_id).first()
    if existing is not None:
        if existing.sender_id != me["id"] or existing.conv_id != conv_id:
            raise ChatError("CLIENT_ID_CONFLICT", "clientId 已被占用（其他用户或其他会话）")
        return _msg_out(existing, _me_brief(me)), True, _member_ids(db, conv_id)

    db_max = (
        db.query(func.max(models.Message.seq))
        .filter(models.Message.conv_id == conv_id)
        .scalar()
        or 0
    )
    for _ in range(3):
        seq = _allocate_seq(conv_id, db_max)
        msg = models.Message(
            conv_id=conv_id,
            seq=seq,
            sender_id=me["id"],
            client_id=client_id,
            body=body,
            msg_type="text",
        )
        db.add(msg)
        try:
            # 自己发的消息直接算已读，避免自己给自己制造未读数
            member = db.get(models.ConversationMember, (conv_id, me["id"]))
            if member is not None and (member.last_read_seq or 0) < seq:
                member.last_read_seq = seq
            db.commit()
            db.refresh(msg)
            return _msg_out(msg, _me_brief(me)), False, _member_ids(db, conv_id)
        except IntegrityError:
            db.rollback()
            dup = db.query(models.Message).filter(models.Message.client_id == client_id).first()
            if dup is not None:
                return _msg_out(dup, _me_brief(me)), True, _member_ids(db, conv_id)
            db_max = (
                db.query(func.max(models.Message.seq))
                .filter(models.Message.conv_id == conv_id)
                .scalar()
                or 0
            )
    raise ChatError("INTERNAL", "消息发送冲突，请重试")


def _mark_read(db: Session, uid: int, conv_id: int, seq: int) -> int:
    member = db.get(models.ConversationMember, (conv_id, uid))
    if member is None:
        raise ChatError("NOT_MEMBER", "你不在该会话中")
    max_seq = (
        db.query(func.max(models.Message.seq))
        .filter(models.Message.conv_id == conv_id)
        .scalar()
        or 0
    )
    target = max(0, min(int(seq), max_seq))
    if target > (member.last_read_seq or 0):
        member.last_read_seq = target
        db.commit()
    return member.last_read_seq or 0


# ---------------------------------------------------------------------------
# REST：会话 / 历史 / 已读 / 可选联系人
# ---------------------------------------------------------------------------

class ConversationCreate(BaseModel):
    type: str = "private"
    peerId: Optional[int] = None
    name: str = ""
    memberIds: List[int] = []


class ReadIn(BaseModel):
    seq: int = 0


@router.get("/api/chat/conversations")
def list_conversations(
    db: Session = Depends(get_db),
    user=Depends(require_permission("chat.use")),
):
    """会话列表：最后一条消息 + 未读数 + 对方在线状态。"""
    convs = (
        db.query(models.Conversation)
        .join(
            models.ConversationMember,
            models.ConversationMember.conv_id == models.Conversation.id,
        )
        .filter(models.ConversationMember.user_id == user.id)
        .all()
    )
    items = [_conversation_out(db, c, user.id) for c in convs]
    items = [x for x in items if x]
    items.sort(key=lambda x: x["updatedAt"] or "", reverse=True)
    return items


@router.post("/api/chat/conversations")
def create_conversation(
    body: ConversationCreate,
    db: Session = Depends(get_db),
    user=Depends(require_permission("chat.use")),
):
    """创建私聊（自动复用已有会话）或群聊。"""
    if body.type == "private":
        if not body.peerId or body.peerId == user.id:
            raise HTTPException(status_code=400, detail="请选择聊天对象")
        peer = db.get(models.User, body.peerId)
        if not peer or not peer.is_active or peer.status != "active":
            raise HTTPException(status_code=404, detail="对方账号不可用")

        existing = _find_private(db, user.id, peer.id)
        if existing:
            return _conversation_out(db, existing, user.id)

        conv = models.Conversation(type="private", owner_id=user.id)
        db.add(conv)
        db.flush()
        db.add_all([
            models.ConversationMember(conv_id=conv.id, user_id=user.id),
            models.ConversationMember(conv_id=conv.id, user_id=peer.id),
        ])
        db.commit()
        db.refresh(conv)
        return _conversation_out(db, conv, user.id)

    if body.type != "group":
        raise HTTPException(status_code=400, detail="不支持的会话类型")

    name = body.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="群聊名称不能为空")
    if len(name) > 60:
        raise HTTPException(status_code=400, detail="群聊名称过长")

    member_ids = {int(i) for i in body.memberIds} | {user.id}
    members = (
        db.query(models.User)
        .filter(models.User.id.in_(member_ids), models.User.is_active == True)  # noqa: E712
        .all()
    )
    if len(members) < 2:
        raise HTTPException(status_code=400, detail="群聊至少需要两个成员")

    conv = models.Conversation(type="group", name=name, owner_id=user.id)
    db.add(conv)
    db.flush()
    db.add_all([
        models.ConversationMember(conv_id=conv.id, user_id=u.id) for u in members
    ])
    db.commit()
    db.refresh(conv)
    return _conversation_out(db, conv, user.id)


def _find_private(db: Session, a: int, b: int):
    rows = (
        db.query(models.ConversationMember.conv_id)
        .join(
            models.Conversation,
            models.Conversation.id == models.ConversationMember.conv_id,
        )
        .filter(
            models.Conversation.type == "private",
            models.ConversationMember.user_id.in_([a, b]),
        )
        .group_by(models.ConversationMember.conv_id)
        .having(func.count(models.ConversationMember.user_id) == 2)
        .all()
    )
    for (conv_id,) in rows:
        conv = db.get(models.Conversation, conv_id)
        if conv and len(conv.members) == 2:
            return conv
    return None


@router.get("/api/chat/conversations/{conv_id}/messages")
def list_messages(
    conv_id: int,
    afterSeq: int = Query(0, alias="afterSeq"),
    beforeSeq: Optional[int] = Query(None, alias="beforeSeq"),
    limit: int = Query(50, ge=1, le=config.CHAT_HISTORY_LIMIT),
    db: Session = Depends(get_db),
    user=Depends(require_permission("chat.use")),
):
    """历史 / 增量同步。

    - afterSeq=N：拉取 seq > N 的消息（重连补洞、离线同步，P12）
    - beforeSeq=N：向上翻页
    - 都不传：最近 limit 条
    """
    member = db.get(models.ConversationMember, (conv_id, user.id))
    if member is None:
        raise HTTPException(status_code=404, detail="会话不存在或你不在其中")

    q = (
        db.query(models.Message, models.User)
        .join(models.User, models.User.id == models.Message.sender_id)
        .filter(models.Message.conv_id == conv_id)
    )
    if afterSeq and afterSeq > 0:
        rows = (
            q.filter(models.Message.seq > afterSeq)
            .order_by(models.Message.seq.asc())
            .limit(limit)
            .all()
        )
    elif beforeSeq:
        rows = (
            q.filter(models.Message.seq < beforeSeq)
            .order_by(models.Message.seq.desc())
            .limit(limit)
            .all()
        )
        rows.reverse()
    else:
        rows = (
            q.order_by(models.Message.seq.desc()).limit(limit).all()
        )
        rows.reverse()

    last_seq = (
        db.query(func.max(models.Message.seq))
        .filter(models.Message.conv_id == conv_id)
        .scalar()
        or 0
    )
    return {
        "messages": [_msg_out(m, _user_brief(u)) for m, u in rows],
        "lastSeq": last_seq,
        "hasMore": len(rows) == limit,
    }


@router.post("/api/chat/conversations/{conv_id}/read")
def mark_read(
    conv_id: int,
    body: ReadIn,
    db: Session = Depends(get_db),
    user=Depends(require_permission("chat.use")),
):
    try:
        last_read = _mark_read(db, user.id, conv_id, body.seq)
    except ChatError as exc:
        raise HTTPException(status_code=404, detail=exc.message)
    max_seq = (
        db.query(func.max(models.Message.seq))
        .filter(models.Message.conv_id == conv_id)
        .scalar()
        or 0
    )
    return {"lastReadSeq": last_read, "unread": max(0, max_seq - last_read)}


@router.get("/api/chat/users")
def chat_users(
    db: Session = Depends(get_db),
    user=Depends(require_permission("chat.use")),
):
    """可发起会话的用户列表（排除自己和管理员）。"""
    users = (
        db.query(models.User)
        .filter(models.User.is_active == True, models.User.status == "active")  # noqa: E712
        .order_by(models.User.id)
        .all()
    )
    result = []
    for u in users:
        if u.id == user.id:
            continue
        codes = {r.code for r in u.roles}
        if "admin" in codes:
            continue
        if "chat.use" not in get_permissions(u, db):
            continue
        result.append({
            **_user_brief(u),
            "major": u.major,
            "roles": sorted(codes),
        })
    return result


# ---------------------------------------------------------------------------
# WebSocket
# ---------------------------------------------------------------------------

def _authenticate(db: Session, token: str) -> Optional[dict]:
    """握手鉴权（P16）：token 无效、账号停用、无聊天权限，一律拒绝。"""
    user = token_user(db, token)
    if user is None or "chat.use" not in get_permissions(user, db):
        return None
    return _user_brief(user)


async def _safe_send(ws: WebSocket, payload: dict) -> bool:
    try:
        await ws.send_text(json.dumps(payload, ensure_ascii=False))
        return True
    except Exception:  # noqa: BLE001
        return False


async def _send_error(ws: WebSocket, code: str, message: str, client_id: str = ""):
    payload = {"type": "error", "code": code, "message": message}
    if client_id:
        payload["clientId"] = client_id
    await _safe_send(ws, payload)


async def _broadcast_presence(uid: int, online: bool):
    try:
        peers = await _db(lambda db: _peer_ids(db, uid))
    except Exception:  # noqa: BLE001 - 在线状态广播失败不影响主流程
        return
    await chat_hub.broadcast_to(
        peers, {"type": "presence", "userId": uid, "online": online}
    )


# 同一会话的落库操作串行化：即使 Redis 不可用，DB 发号也不会撞车
_conv_locks: dict = {}


def _conv_lock(conv_id: int) -> asyncio.Lock:
    lock = _conv_locks.get(conv_id)
    if lock is None:
        lock = asyncio.Lock()
        _conv_locks[conv_id] = lock
    return lock


async def _handle_chat(ws: WebSocket, me: dict, data: dict):
    conv_id = data.get("convId")
    client_id = str(data.get("clientId") or "").strip()
    body = str(data.get("body") or "").strip()

    if not isinstance(conv_id, int) or conv_id <= 0:
        return await _send_error(ws, "BAD_REQUEST", "convId 不合法", client_id)
    if not client_id or len(client_id) > 128:
        return await _send_error(ws, "BAD_REQUEST", "缺少 clientId", client_id)
    if not body:
        return await _send_error(ws, "BAD_REQUEST", "消息不能为空", client_id)
    if len(body) > config.CHAT_MAX_BODY:
        return await _send_error(ws, "BAD_REQUEST", "消息过长", client_id)

    async with _conv_lock(conv_id):
        try:
            msg, duplicated, member_ids = await _db(
                lambda db: _persist_message(db, me, conv_id, client_id, body)
            )
        except ChatError as exc:
            return await _send_error(ws, exc.code, exc.message, client_id)
        except Exception:  # noqa: BLE001 - 不能因为一条消息打挂长连接
            return await _send_error(ws, "INTERNAL", "消息发送失败，请重试", client_id)

    # 先回执：发送方把「转圈」变成「对勾」（P10）
    await _safe_send(ws, {
        "type": "ack",
        "clientId": client_id,
        "convId": conv_id,
        "seq": msg["seq"],
        "msgId": msg["id"],
        "createdAt": msg["createdAt"],
        "duplicate": duplicated,
    })

    if duplicated:
        return  # 重发消息：只补回执，不重复投递

    # 消息已经落库，投递只是「顺手的事」；失败由客户端 sync 兜底（P12）
    for uid in member_ids:
        await chat_hub.send_to_user(
            uid,
            {"type": "chat", "message": msg},
            exclude=ws if uid == me["id"] else None,
        )

    await run_in_threadpool(
        mq.publish_event,
        "chat.message",
        me["account"],
        me["nickname"],
        f"在会话 {conv_id} 发送了一条消息",
        me["id"],
    )


async def _handle_read(ws: WebSocket, me: dict, data: dict):
    conv_id = data.get("convId")
    seq = data.get("seq")
    if not isinstance(conv_id, int) or not isinstance(seq, int):
        return await _send_error(ws, "BAD_REQUEST", "已读参数不合法")
    try:
        last_read = await _db(lambda db: _mark_read(db, me["id"], conv_id, seq))
    except ChatError as exc:
        return await _send_error(ws, exc.code, exc.message)
    await _safe_send(ws, {
        "type": "read", "convId": conv_id, "lastReadSeq": last_read,
    })


@router.websocket("/ws/chat")
async def chat_ws(
    websocket: WebSocket,
    token: str = Query(""),
    device: str = Query("web"),
):
    await websocket.accept()

    me = await _db(lambda db: _authenticate(db, token))
    if me is None:
        await _send_error(websocket, "UNAUTHORIZED", "登录状态无效或无权使用聊天")
        await websocket.close(code=4401)
        return

    uid = me["id"]
    device = (device or "web")[:32]
    first_connection = await chat_hub.register(uid, websocket, device)
    chat_hub.mark_online(uid, device)
    if first_connection:
        await _broadcast_presence(uid, True)

    recent = deque()
    try:
        while True:
            try:
                raw = await asyncio.wait_for(
                    websocket.receive_text(), timeout=config.CHAT_HEARTBEAT_TIMEOUT
                )
            except asyncio.TimeoutError:
                # 半开连接：长时间没有任何数据（连 ping 都没有）→ 服务端主动回收
                await websocket.close(code=4408)
                break

            now = time.monotonic()
            while recent and now - recent[0] > config.CHAT_RATE_WINDOW:
                recent.popleft()

            try:
                data = json.loads(raw)
            except (TypeError, ValueError):
                await _send_error(websocket, "BAD_JSON", "消息不是合法 JSON")
                continue

            msg_type = data.get("type")
            if msg_type == "ping":
                chat_hub.mark_online(uid, device)  # 心跳续期在线状态（P13）
                await _safe_send(websocket, {"type": "pong", "ts": int(time.time() * 1000)})
            elif msg_type == "chat":
                if len(recent) >= config.CHAT_RATE_LIMIT:
                    await _send_error(
                        websocket, "RATE_LIMIT", "发送太频繁，请稍后再试",
                        str(data.get("clientId") or ""),
                    )
                    continue
                recent.append(now)
                await _handle_chat(websocket, me, data)
            elif msg_type == "read":
                await _handle_read(websocket, me, data)
            else:
                await _send_error(websocket, "BAD_TYPE", f"未知消息类型：{msg_type}")
    except WebSocketDisconnect:
        pass
    finally:
        _, fully_offline = await chat_hub.unregister(uid, websocket)
        if fully_offline:
            chat_hub.mark_offline(uid, device)
            await _broadcast_presence(uid, False)
