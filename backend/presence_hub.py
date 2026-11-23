"""实时在线状态（连接级）。

数据大屏原来的「在线用户」是「5 分钟内有 HTTP 请求」，有滞后。
现在改成：登录后主布局统一建立 `/ws/presence` 长连接，连接在即在线，
断开即下线；进程被杀的僵尸连接靠 Redis 分数（过期时间）自动清理。

实现（对应 PPT P13）：
- Redis ZSET `presence:online`：member = 用户 JSON，score = 过期时间（毫秒）；
- 建立连接 ZADD，心跳（30s）续期，最后一条连接断开 ZREM；
- 大屏读取时先清理过期分数，再 ZCARD 计数 / ZREVRANGE 取前几名；
- Redis 不可用时退回本进程连接表（单进程部署仍能实时显示）。
"""
import json
import threading
import time

import config
import redis_client

_lock = threading.Lock()
# uid -> {"user": {...}, "sockets": {WebSocket: device}}
_conns: dict = {}


def _now_ms() -> int:
    return int(time.time() * 1000)


def _member(user: dict) -> str:
    # sort_keys 保证同一个用户每次序列化结果一致，ZREM 才能精确删除
    return json.dumps(user, ensure_ascii=False, sort_keys=True)


def _zadd(user: dict):
    expire_at = _now_ms() + config.PRESENCE_TTL * 1000
    redis_client.run(
        lambda c: c.zadd(config.PRESENCE_KEY, {_member(user): expire_at})
    )


def _zrem(user: dict):
    redis_client.run(lambda c: c.zrem(config.PRESENCE_KEY, _member(user)))


def register(uid: int, user: dict, ws, device: str = "") -> bool:
    """注册连接。返回是否是该用户的第一条连接。"""
    with _lock:
        entry = _conns.setdefault(uid, {"user": user, "sockets": {}})
        entry["user"] = user
        entry["sockets"][ws] = device
        first = len(entry["sockets"]) == 1
    if first:
        _zadd(user)
    return first


def refresh(uid: int):
    """心跳续期。"""
    with _lock:
        entry = _conns.get(uid)
        user = dict(entry["user"]) if entry else None
    if user:
        _zadd(user)


def unregister(uid: int, ws) -> bool:
    """注销连接。返回该用户是否已完全离线。"""
    with _lock:
        entry = _conns.get(uid)
        if entry is None:
            return False
        entry["sockets"].pop(ws, None)
        last = not entry["sockets"]
        user = dict(entry["user"]) if last else None
        if last:
            _conns.pop(uid, None)
    if last:
        _zrem(user)
    return last


def count() -> int:
    """当前实时在线人数（供采样线程使用）。"""
    now = _now_ms()

    def op(c):
        c.zremrangebyscore(config.PRESENCE_KEY, 0, now)
        return int(c.zcard(config.PRESENCE_KEY))

    value = redis_client.run(op)
    if value is not None:
        return value
    with _lock:
        return len(_conns)


def snapshot() -> dict:
    """在线人数 + 前 10 名用户，结构与旧版 online_snapshot 保持一致。"""
    now = _now_ms()
    ttl_ms = config.PRESENCE_TTL * 1000

    def op(c):
        c.zremrangebyscore(config.PRESENCE_KEY, 0, now)
        total = int(c.zcard(config.PRESENCE_KEY))
        rows = c.zrevrange(config.PRESENCE_KEY, 0, 9, withscores=True)
        users = []
        for member, score in rows:
            try:
                data = json.loads(member)
            except (TypeError, ValueError):
                continue
            # score 是过期时间，倒推最后一次心跳时间
            data["last_active"] = max(0, int(score) - ttl_ms)
            users.append(data)
        return {"count": total, "users": users, "source": "redis"}

    data = redis_client.run(op)
    if data is not None:
        return data

    with _lock:
        users = []
        for entry in list(_conns.values())[:10]:
            data = dict(entry["user"])
            data["last_active"] = now
            users.append(data)
        return {"count": len(_conns), "users": users, "source": "local"}
