"""Redis 连接与基础操作封装。

设计原则：Redis 只是数据大屏的增强能力，任何 Redis 异常都不能影响主业务。
- 连接失败后 20 秒内不再重试，避免每个请求都卡在连接超时上；
- 所有操作失败都返回 None，由调用方决定降级逻辑。
"""
import json
import threading
import time

import redis

import config

_client = None
_retry_at = 0.0
_last_error = None
_lock = threading.Lock()

# 用流水线记录大屏数据的缓存命中/未命中
CACHE_HIT = "stats:cache:app_hits"
CACHE_MISS = "stats:cache:app_misses"


def _connect():
    client = redis.Redis.from_url(
        config.REDIS_URL,
        decode_responses=True,
        socket_connect_timeout=0.6,
        # 普通命令读超时；连接超时单独设置，避免 Redis 未启动时拖慢业务
        socket_timeout=3.0,
        health_check_interval=15,
    )
    client.ping()
    return client


def get_client():
    """返回可用连接；Redis 不可用时快速返回 None。"""
    global _client, _retry_at, _last_error
    now = time.time()
    if _client is not None:
        return _client
    if now < _retry_at:
        return None
    with _lock:
        if _client is not None:
            return _client
        if now < _retry_at:
            return None
        try:
            _client = _connect()
            _retry_at = 0.0
            _last_error = None
        except Exception as exc:  # noqa: BLE001 - 需要兜住所有网络异常
            _last_error = str(exc)
            _client = None
            _retry_at = now + 20
    return _client


def reset_client(delay=3.0):
    """命令失败后主动断开，稍后再重连。"""
    global _client, _retry_at, _last_error
    _client = None
    _retry_at = time.time() + delay


def run(fn, default=None):
    """执行一个 Redis 操作，异常时返回 default。"""
    global _last_error
    client = get_client()
    if client is None:
        return default
    try:
        return fn(client)
    except Exception as exc:  # noqa: BLE001
        _last_error = str(exc)
        try:
            client.close()
        except Exception:  # noqa: BLE001
            pass
        reset_client()
        return default


def is_connected():
    return get_client() is not None


def last_error():
    return _last_error


# ---------------------------------------------------------------------------
# 缓存
# ---------------------------------------------------------------------------

def cache_get_json(key):
    """读取 JSON 缓存；读到/读不到都会记录应用层命中统计。"""
    raw = run(lambda c: c.get(key))
    if raw:
        run(lambda c: c.incr(CACHE_HIT))
        try:
            return json.loads(raw)
        except (TypeError, ValueError):
            return None
    run(lambda c: c.incr(CACHE_MISS))
    return None


def cache_set_json(key, value, ttl):
    return run(lambda c: c.setex(key, ttl, json.dumps(value, ensure_ascii=False)))


def cache_stats():
    hits = run(lambda c: c.get(CACHE_HIT), 0) or 0
    misses = run(lambda c: c.get(CACHE_MISS), 0) or 0
    total = int(hits) + int(misses)
    rate = round(int(hits) / total * 100, 1) if total else 0.0
    return {"hits": int(hits), "misses": int(misses), "total": total, "hit_rate": rate}


# ---------------------------------------------------------------------------
# 在线用户（Sorted Set，score 为最后活跃时间）
# ---------------------------------------------------------------------------

def touch_online(user):
    """把用户标记为在线；5 分钟没有请求会自动过期。"""
    now_ms = int(time.time() * 1000)
    member = json.dumps(
        {"id": user.id, "account": user.account, "nickname": user.nickname},
        ensure_ascii=False,
    )

    def op(c):
        pipe = c.pipeline()
        pipe.zadd(config.ONLINE_KEY, {member: now_ms})
        pipe.zremrangebyscore(config.ONLINE_KEY, 0, now_ms - config.ONLINE_WINDOW_MS)
        pipe.execute()

    return run(op)


def online_snapshot():
    now_ms = int(time.time() * 1000)
    cutoff = now_ms - config.ONLINE_WINDOW_MS

    def op(c):
        c.zremrangebyscore(config.ONLINE_KEY, 0, cutoff)
        count = c.zcount(config.ONLINE_KEY, cutoff, "+inf")
        rows = c.zrevrange(config.ONLINE_KEY, 0, 9, withscores=True)
        users = []
        for member, score in rows:
            try:
                data = json.loads(member)
            except (TypeError, ValueError):
                continue
            data["last_active"] = int(score)
            users.append(data)
        return {"count": int(count), "users": users}

    return run(op, {"count": 0, "users": []})


# ---------------------------------------------------------------------------
# Redis 服务自身指标
# ---------------------------------------------------------------------------

def redis_snapshot():
    def op(c):
        info = c.info()
        hits = int(info.get("keyspace_hits", 0) or 0)
        misses = int(info.get("keyspace_misses", 0) or 0)
        total = hits + misses
        return {
            "connected": True,
            "url": config.REDIS_URL,
            "version": info.get("redis_version", ""),
            "memory_bytes": int(info.get("used_memory", 0) or 0),
            "memory_human": info.get("used_memory_human", "0B").strip(),
            "peak_memory_human": info.get("used_memory_peak_human", "0B").strip(),
            "keys": int(c.dbsize()),
            "ops_per_sec": int(info.get("instantaneous_ops_per_sec", 0) or 0),
            "clients": int(info.get("connected_clients", 0) or 0),
            "uptime_seconds": int(info.get("uptime_in_seconds", 0) or 0),
            "server_hit_rate": round(hits / total * 100, 1) if total else 0.0,
            "keyspace_hits": hits,
            "keyspace_misses": misses,
        }

    return run(op, {"connected": False, "url": config.REDIS_URL, "error": last_error()})
