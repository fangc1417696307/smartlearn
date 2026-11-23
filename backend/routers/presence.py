"""实时在线状态 WebSocket。

登录后的主布局统一连接 `/ws/presence`：连接建立即在线，页面关闭即下线，
心跳每 30s 续期一次 Redis 过期时间。数据大屏的「在线用户」读这份状态。
"""
import asyncio
import json

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from starlette.concurrency import run_in_threadpool

import config
import database
import presence_hub
from deps import token_user

router = APIRouter(tags=["在线状态"])


def _with_db(fn):
    db = database.SessionLocal()
    try:
        return fn(db)
    finally:
        db.close()


async def _db(fn):
    return await run_in_threadpool(_with_db, fn)


async def _safe_send(ws: WebSocket, payload: dict) -> bool:
    try:
        await ws.send_text(json.dumps(payload, ensure_ascii=False))
        return True
    except Exception:  # noqa: BLE001
        return False


def _brief(user) -> dict:
    return {
        "id": user.id,
        "account": user.account,
        "nickname": user.nickname or user.account,
    }


@router.websocket("/ws/presence")
async def presence_ws(
    websocket: WebSocket,
    token: str = Query(""),
    device: str = Query("web"),
):
    await websocket.accept()

    brief = await _db(lambda db: (lambda u: _brief(u) if u else None)(token_user(db, token)))
    if brief is None:
        await _safe_send(websocket, {"type": "error", "code": "UNAUTHORIZED"})
        await websocket.close(code=4401)
        return

    uid = brief["id"]
    presence_hub.register(uid, brief, websocket, (device or "web")[:32])

    try:
        while True:
            try:
                raw = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=config.PRESENCE_HEARTBEAT_TIMEOUT,
                )
            except asyncio.TimeoutError:
                await websocket.close(code=4408)
                break

            try:
                data = json.loads(raw)
            except (TypeError, ValueError):
                continue

            if data.get("type") == "ping":
                presence_hub.refresh(uid)
                await _safe_send(websocket, {"type": "pong"})
    except WebSocketDisconnect:
        pass
    finally:
        presence_hub.unregister(uid, websocket)
