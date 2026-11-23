"""聊天连接中心（WebSocket 网关的「在线表」）。

对应 PPT：
- P06 入口网关：userId -> 连接 的内存表；
- P13 在线状态：Redis 里存 `chat:online:<uid>` = "网关ID|设备"，带 TTL 防僵尸；
- P17 水平扩展：本项目单进程部署，投递走本进程内存表；在线表已在 Redis，
  将来加网关时把 send_to_user 换成 Redis Pub/Sub 频道即可，业务代码不用改。

设计约定：投递失败不报错——消息已经落库，客户端重连后用游标 sync 拉取兜底（P12）。
"""
import asyncio
import json

import config
import redis_client

# uid -> {WebSocket: device}
_conns: dict = {}
_lock = asyncio.Lock()

# 只删除「自己」写的那条在线记录：多端登录时不能把另一台设备的状态删掉
_RELEASE_ONLINE_LUA = """
if redis.call('GET', KEYS[1]) == ARGV[1] then
  return redis.call('DEL', KEYS[1])
end
return 0
"""


def _value(device: str) -> str:
    return f"{config.CHAT_GATEWAY_ID}|{device}"


async def register(uid: int, ws, device: str) -> bool:
    """注册连接，返回是否是该用户的第一条连接（用于广播上线）。"""
    async with _lock:
        devices = _conns.setdefault(uid, {})
        devices[ws] = device
        return len(devices) == 1


async def unregister(uid: int, ws) -> tuple:
    """注销连接，返回 (device, 是否已完全离线)。"""
    async with _lock:
        devices = _conns.get(uid)
        device = None
        if devices:
            device = devices.pop(ws, None)
            if not devices:
                _conns.pop(uid, None)
        return device, not _conns.get(uid)


def mark_online(uid: int, device: str):
    """上线 / 心跳续期：SET chat:online:<uid> "gw1|web" EX 90（P13）。"""
    key = config.CHAT_ONLINE_KEY.format(uid=uid)
    redis_client.run(
        lambda c: c.set(key, _value(device), ex=config.CHAT_ONLINE_TTL)
    )


def mark_offline(uid: int, device: str):
    """下线：用 Lua 比对 value，防止误删另一台设备的在线状态（P13）。"""
    key = config.CHAT_ONLINE_KEY.format(uid=uid)
    redis_client.run(
        lambda c: c.eval(_RELEASE_ONLINE_LUA, 1, key, _value(device))
    )


def is_online(uid: int) -> bool:
    """本进程有连接，或 Redis 在线表里有记录（多端 / 多网关）。"""
    if _conns.get(uid):
        return True
    key = config.CHAT_ONLINE_KEY.format(uid=uid)
    return bool(redis_client.run(lambda c: c.exists(key), 0))


def local_online_ids() -> list:
    return list(_conns.keys())


async def send_to_user(uid: int, payload: dict, exclude=None) -> int:
    """给某个用户的所有本机连接发消息（多端投递，P13）。返回成功条数。

    exclude：发起消息的那条连接（发送方靠 ack 更新状态，不重复收 chat 事件）。
    """
    async with _lock:
        sockets = [s for s in _conns.get(uid, {}).keys() if s is not exclude]
    if not sockets:
        return 0
    data = json.dumps(payload, ensure_ascii=False)
    delivered = 0
    dead = []
    for ws in sockets:
        try:
            await ws.send_text(data)
            delivered += 1
        except Exception:  # noqa: BLE001 - 连接已断，交给 sync 兜底
            dead.append(ws)
    if dead:
        async with _lock:
            devices = _conns.get(uid)
            if devices:
                for ws in dead:
                    devices.pop(ws, None)
                if not devices:
                    _conns.pop(uid, None)
    return delivered


async def broadcast_to(uids, payload: dict):
    for uid in set(uids):
        await send_to_user(uid, payload)
