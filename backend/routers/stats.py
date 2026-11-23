from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

import config
import models
import mq
import presence_hub
import redis_client
from database import get_db
from deps import require_permission

router = APIRouter(prefix="/api/stats", tags=["数据看板"])


def _overview(db: Session):
    """从 SQLite 聚合业务数据。"""
    total = db.query(func.count(models.User.id)).scalar() or 0
    pending = db.query(func.count(models.User.id)).filter(models.User.status == "pending").scalar() or 0

    role_rows = (
        db.query(models.Role.name, func.count(models.User.id))
        .join(models.user_roles, models.Role.id == models.user_roles.c.role_id)
        .join(models.User, models.User.id == models.user_roles.c.user_id)
        .group_by(models.Role.name)
        .all()
    )

    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    today_new = db.query(func.count(models.User.id)).filter(models.User.created_at >= today_start).scalar() or 0

    last7 = []
    for i in range(6, -1, -1):
        d = today_start - timedelta(days=i)
        d2 = d + timedelta(days=1)
        cnt = db.query(func.count(models.User.id)).filter(models.User.created_at >= d, models.User.created_at < d2).scalar() or 0
        last7.append({"date": d.strftime("%m-%d"), "count": cnt})

    return {
        "total_users": total,
        "pending_users": pending,
        "today_new": today_new,
        "role_distribution": [{"name": n, "count": c} for n, c in role_rows],
        "last_7_days": last7,
    }


def _overview_cached(db: Session):
    """业务数据走 Redis 缓存（TTL 5 秒），同时产生真实的缓存命中/未命中。"""
    cached = redis_client.cache_get_json(config.CACHE_OVERVIEW_KEY)
    if cached is not None:
        return cached
    data = _overview(db)
    redis_client.cache_set_json(config.CACHE_OVERVIEW_KEY, data, config.CACHE_OVERVIEW_TTL)
    return data


@router.get("/overview")
def overview(db: Session = Depends(get_db), user=Depends(require_permission("stats.view"))):
    return _overview_cached(db)


@router.get("/bigscreen")
def bigscreen(db: Session = Depends(get_db), user=Depends(require_permission("stats.view"))):
    """数据大屏：业务指标 + Redis 缓存指标 + Kafka 消息队列指标。"""
    return {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "overview": _overview_cached(db),
        "redis": {
            **redis_client.redis_snapshot(),
            "cache": redis_client.cache_stats(),
            "cache_ttl": config.CACHE_OVERVIEW_TTL,
        },
        "mq": mq.snapshot(),
        "online": presence_hub.snapshot(),
        "events": mq.recent_events(20),
    }


# 演示用事件模板：点一下「模拟活动」就能看到大屏数据动起来
_DEMO_EVENTS = [
    ("login", "2024080805", "小陈", "密码登录"),
    ("login", "student01", "演示学生", "邮箱验证码登录"),
    ("register", "2024090101", "新同学", "学生注册"),
    ("resource_generate", "2024080805", "小陈", "生成「数据结构 · 二叉树」学习资源"),
    ("qa_ask", "2024080805", "小陈", "提问：哈希冲突怎么解决？"),
    ("assessment", "2024080805", "小陈", "完成「操作系统」章节测评"),
    ("path_update", "student01", "演示学生", "更新学习路径进度"),
    ("teacher_approve", "20240001", "王老师", "教师账号审核通过"),
]


@router.post("/demo-events")
def demo_events(count: int = 8, user=Depends(require_permission("stats.view"))):
    """演示用：向消息队列投递若干条模拟事件。"""
    count = max(1, min(count, 30))
    produced = 0
    for i in range(count):
        event_type, account, nickname, detail = _DEMO_EVENTS[i % len(_DEMO_EVENTS)]
        if mq.publish_event(event_type, account=account, nickname=nickname, detail=detail):
            produced += 1
    return {"ok": True, "produced": produced}
