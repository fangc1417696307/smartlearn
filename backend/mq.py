"""基于 Apache Kafka 的消息队列。

真实的生产者 / 消费者模型：
- 业务侧调用 publish_event() 把事件 produce 到 Kafka topic；
- 后台消费者组 bigscreen 订阅 topic、消费事件并同步提交 offset；
- 采样线程每秒记录生产/消费速率与在线人数，供数据大屏绘制曲线；
- Kafka 不可用时整个模块自动降级为 no-op，不影响主业务。

大屏指标里的累计生产/消费计数、最近事件列表、吞吐曲线存放在 Redis，
队列积压 / 消费者 Lag / 分区数直接从 Kafka 读取。
"""
import json
import os
import socket
import threading
import time
import uuid

from confluent_kafka import (
    Consumer,
    ConsumerGroupTopicPartitions,
    KafkaError,
    KafkaException,
    Producer,
    TopicPartition,
)
from confluent_kafka.admin import AdminClient, NewTopic

import config
import presence_hub
import redis_client

_stop = threading.Event()
_threads = []
_client_id = f"smartlearn-{socket.gethostname()}-{os.getpid()}"
_lock = threading.Lock()
_producer = None
_producer_retry_at = 0.0
_metrics = None
_snapshot_cache = {"at": 0.0, "data": None}
_snapshot_fail_at = 0.0
_snapshot_lock = threading.Lock()


def _kafka_config():
    return {
        "bootstrap.servers": config.KAFKA_BOOTSTRAP_SERVERS,
        "client.id": _client_id,
        "socket.timeout.ms": 2000,
    }


# ---------------------------------------------------------------------------
# 生产者
# ---------------------------------------------------------------------------

def _get_producer():
    global _producer, _producer_retry_at
    now = time.time()
    if _producer is not None:
        return _producer
    if now < _producer_retry_at:
        return None
    with _lock:
        if _producer is not None:
            return _producer
        if now < _producer_retry_at:
            return None
        try:
            producer = Producer({
                **_kafka_config(),
                "acks": "all",
                "retries": 3,
                "linger.ms": 10,
                "message.timeout.ms": 5000,
            })
            # 首次创建时做一次快速连通性检查，Kafka 没启动时不要卡住业务
            producer.list_topics(timeout=1.5)
            _producer = producer
            _producer_retry_at = 0.0
        except Exception:  # noqa: BLE001
            _producer = None
            _producer_retry_at = now + 5
    return _producer


def _reset_producer():
    global _producer, _producer_retry_at
    _producer = None
    _producer_retry_at = time.time() + 5


def _on_delivery(err, _msg):
    if err is None:
        redis_client.run(lambda c: c.incr(config.MQ_PRODUCED_KEY))


def publish_event(event_type, account="", nickname="", detail="", user_id=""):
    """向 Kafka 投递一条事件。返回事件 ID，失败返回 None。"""
    producer = _get_producer()
    if producer is None:
        return None
    msg_id = uuid.uuid4().hex
    payload = {
        "id": msg_id,
        "type": str(event_type),
        "account": str(account or ""),
        "nickname": str(nickname or ""),
        "detail": str(detail or ""),
        "user_id": str(user_id or ""),
        "ts": str(int(time.time() * 1000)),
    }
    try:
        producer.produce(
            config.KAFKA_TOPIC,
            key=str(account or event_type),
            value=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            callback=_on_delivery,
        )
        # 触发投递回调（异步）
        producer.poll(0)
        return msg_id
    except Exception:  # noqa: BLE001
        _reset_producer()
        return None


# ---------------------------------------------------------------------------
# 消费者
# ---------------------------------------------------------------------------

def _ensure_topic():
    """确保 topic 存在；首次启动时自动创建 3 个分区。"""
    admin = AdminClient(_kafka_config())
    metadata = admin.list_topics(timeout=3)
    if config.KAFKA_TOPIC in metadata.topics and metadata.topics[config.KAFKA_TOPIC].error is None:
        return
    futures = admin.create_topics([
        NewTopic(
            config.KAFKA_TOPIC,
            num_partitions=config.KAFKA_PARTITIONS,
            replication_factor=1,
        )
    ])
    for _topic, future in futures.items():
        try:
            future.result(timeout=10)
        except Exception:  # noqa: BLE001 - 已存在等情况直接忽略
            pass


def _handle_payload(raw):
    try:
        event = json.loads(raw.decode("utf-8"))
    except (TypeError, ValueError, AttributeError):
        return
    if "id" not in event:
        event["id"] = uuid.uuid4().hex
    try:
        event["ts"] = int(event.get("ts", 0) or 0)
    except (TypeError, ValueError):
        event["ts"] = 0
    redis_client.run(lambda c: c.incr(config.MQ_CONSUMED_KEY))
    redis_client.run(lambda c: c.lpush(
        config.MQ_RECENT_KEY, json.dumps(event, ensure_ascii=False)
    ))
    redis_client.run(lambda c: c.ltrim(config.MQ_RECENT_KEY, 0, 49))


def _consume_loop():
    consumer = None
    while not _stop.is_set():
        try:
            if consumer is None:
                _ensure_topic()
                consumer = Consumer({
                    **_kafka_config(),
                    "group.id": config.KAFKA_GROUP,
                    "auto.offset.reset": "earliest",
                    "enable.auto.commit": False,
                    "session.timeout.ms": 10000,
                    "max.poll.interval.ms": 300000,
                })
                consumer.subscribe([config.KAFKA_TOPIC])
            msg = consumer.poll(1.0)
            if msg is None:
                continue
            if msg.error():
                if msg.error().code() == KafkaError._PARTITION_EOF:
                    continue
                raise KafkaException(msg.error())
            _handle_payload(msg.value())
            consumer.commit(message=msg, asynchronous=False)
        except Exception:  # noqa: BLE001 - 后台线程需要自愈
            if consumer is not None:
                try:
                    consumer.close()
                except Exception:  # noqa: BLE001
                    pass
            consumer = None
            _stop.wait(2)
    if consumer is not None:
        try:
            consumer.close()
        except Exception:  # noqa: BLE001
            pass


# ---------------------------------------------------------------------------
# 采样器：每秒记录吞吐量，供大屏画曲线
# ---------------------------------------------------------------------------

def _sample_loop():
    last_produced = None
    last_consumed = None
    while not _stop.is_set():
        _stop.wait(1)
        producer = _get_producer()
        if producer is not None:
            try:
                producer.poll(0)
            except Exception:  # noqa: BLE001
                _reset_producer()
        client = redis_client.get_client()
        if client is None:
            last_produced = last_consumed = None
            continue
        try:
            produced = int(client.get(config.MQ_PRODUCED_KEY) or 0)
            consumed = int(client.get(config.MQ_CONSUMED_KEY) or 0)
            now_ms = int(time.time() * 1000)
            # 连接级实时在线人数（presence_hub 自己处理 Redis 降级）
            online = presence_hub.count()
            d_produced = 0 if last_produced is None else max(0, produced - last_produced)
            d_consumed = 0 if last_consumed is None else max(0, consumed - last_consumed)
            last_produced, last_consumed = produced, consumed
            sample = {"t": now_ms, "produced": d_produced, "consumed": d_consumed, "online": online}
            pipe = client.pipeline()
            pipe.rpush(config.MQ_SERIES_KEY, json.dumps(sample))
            pipe.ltrim(config.MQ_SERIES_KEY, -60, -1)
            pipe.expire(config.MQ_SERIES_KEY, 600)
            pipe.execute()
        except Exception:  # noqa: BLE001
            redis_client.reset_client()
            last_produced = last_consumed = None


def start():
    """启动后台消费者与采样线程（幂等）。"""
    global _threads
    if any(t.is_alive() for t in _threads):
        return
    _stop.clear()
    _threads = [
        threading.Thread(target=_consume_loop, daemon=True, name="kafka-consumer"),
        threading.Thread(target=_sample_loop, daemon=True, name="kafka-sampler"),
    ]
    for t in _threads:
        t.start()


def stop():
    _stop.set()


# ---------------------------------------------------------------------------
# 大屏快照
# ---------------------------------------------------------------------------

def _degraded(error=None):
    return {
        "connected": False,
        "backend": "Kafka",
        "topic": config.KAFKA_TOPIC,
        "group": config.KAFKA_GROUP,
        "partitions": 0,
        "length": 0,
        "produced": 0,
        "consumed": 0,
        "pending": 0,
        "lag": 0,
        "consumers": 0,
        "series": [],
        "error": error,
    }


def _metrics_client():
    global _metrics
    with _lock:
        if _metrics is None:
            _metrics = Consumer({
                **_kafka_config(),
                "group.id": config.KAFKA_GROUP + "-metrics",
                "enable.auto.commit": False,
            })
        return _metrics


def _read_kafka_metrics():
    admin = AdminClient(_kafka_config())
    metadata = admin.list_topics(timeout=2)
    topic_meta = metadata.topics.get(config.KAFKA_TOPIC)
    if topic_meta is None or topic_meta.error is not None:
        return {"connected": True, "partitions": 0, "length": 0, "lag": 0, "consumers": 0}

    parts = sorted(topic_meta.partitions.keys())
    consumer = _metrics_client()
    total_length = 0
    low_offsets = {}
    high_offsets = {}
    for p in parts:
        tp = TopicPartition(config.KAFKA_TOPIC, p)
        try:
            low, high = consumer.get_watermark_offsets(tp, timeout=1)
        except Exception:  # noqa: BLE001
            low, high = 0, 0
        low_offsets[p] = low
        high_offsets[p] = high
        total_length += max(0, high - low)

    committed = {}
    try:
        futures = admin.list_consumer_group_offsets([
            ConsumerGroupTopicPartitions(config.KAFKA_GROUP)
        ])
        result = futures[config.KAFKA_GROUP].result(timeout=3)
        for tp in result.topic_partitions:
            if tp.topic == config.KAFKA_TOPIC and tp.offset is not None and tp.offset >= 0:
                committed[tp.partition] = tp.offset
    except Exception:  # noqa: BLE001 - group 尚未创建
        pass

    lag = 0
    for p in parts:
        high = high_offsets.get(p, 0)
        low = low_offsets.get(p, 0)
        c = committed.get(p)
        if c is None or c < 0:
            lag += max(0, high - low)
        else:
            lag += max(0, high - c)

    consumers = 0
    try:
        futures = admin.describe_consumer_groups([config.KAFKA_GROUP])
        desc = futures[config.KAFKA_GROUP].result(timeout=3)
        consumers = len(desc.members)
    except Exception:  # noqa: BLE001
        pass

    return {
        "connected": True,
        "partitions": len(parts),
        "length": total_length,
        "lag": lag,
        "consumers": consumers,
    }


def snapshot():
    """Kafka 指标。Kafka 不可用时返回降级结构，并短暂缓存失败结果。"""
    global _snapshot_fail_at
    now = time.time()
    with _snapshot_lock:
        if _snapshot_cache["data"] is not None and now - _snapshot_cache["at"] < 1.5:
            return _snapshot_cache["data"]
        if now < _snapshot_fail_at:
            return _degraded("Kafka 未连接")

    series = []
    client = redis_client.get_client()
    if client is not None:
        try:
            for raw in client.lrange(config.MQ_SERIES_KEY, -60, -1):
                try:
                    series.append(json.loads(raw))
                except (TypeError, ValueError):
                    continue
        except Exception:  # noqa: BLE001
            redis_client.reset_client()

    produced = 0
    consumed = 0
    if client is not None:
        try:
            produced = int(client.get(config.MQ_PRODUCED_KEY) or 0)
            consumed = int(client.get(config.MQ_CONSUMED_KEY) or 0)
        except Exception:  # noqa: BLE001
            redis_client.reset_client()

    try:
        metrics = _read_kafka_metrics()
        data = {
            "connected": True,
            "backend": "Kafka",
            "topic": config.KAFKA_TOPIC,
            "group": config.KAFKA_GROUP,
            "partitions": metrics["partitions"],
            "length": metrics["length"],
            "produced": produced,
            "consumed": consumed,
            "pending": 0,
            "lag": metrics["lag"],
            "consumers": metrics["consumers"],
            "series": series,
        }
    except Exception as exc:  # noqa: BLE001
        _snapshot_fail_at = time.time() + 3
        data = _degraded(str(exc))

    with _snapshot_lock:
        _snapshot_cache.update(at=time.time(), data=data)
    return data


def recent_events(limit=20):
    def op(c):
        events = []
        for raw in c.lrange(config.MQ_RECENT_KEY, 0, limit - 1):
            try:
                events.append(json.loads(raw))
            except (TypeError, ValueError):
                continue
        return events

    return redis_client.run(op, [])
