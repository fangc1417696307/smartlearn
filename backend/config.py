import os
from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY", "smartlearn-dev-secret-key-change-me")

# SMTP（QQ 邮箱）
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.qq.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "465"))
SMTP_USER = os.getenv("SMTP_USER", "1417696307@qq.com")
SMTP_AUTH_CODE = os.getenv("SMTP_AUTH_CODE", "")

# 管理员初始密码
ADMIN_INITIAL_PASSWORD = os.getenv("ADMIN_INITIAL_PASSWORD", "admin123")

# Redis（数据大屏：缓存 + 在线统计 + 指标采样）
# 使用项目内 backend/tools/redis 启动的独立实例，避开本机已有的 6379 服务
REDIS_URL = os.getenv("REDIS_URL", "redis://127.0.0.1:6380/0")

# 消息队列（Kafka）
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "127.0.0.1:9092")
KAFKA_TOPIC = os.getenv("KAFKA_TOPIC", "smartlearn.events")
KAFKA_GROUP = os.getenv("KAFKA_GROUP", "bigscreen")
KAFKA_PARTITIONS = int(os.getenv("KAFKA_PARTITIONS", "3"))

# 统计相关键
MQ_PRODUCED_KEY = "stats:mq:produced"
MQ_CONSUMED_KEY = "stats:mq:consumed"
MQ_RECENT_KEY = "stats:mq:recent"
MQ_SERIES_KEY = "stats:mq:series"
CACHE_OVERVIEW_KEY = "stats:cache:overview"
CACHE_OVERVIEW_TTL = 5  # 秒

# 实时在线状态（连接级）：登录后的页面统一建 WebSocket，心跳续期
PRESENCE_KEY = "presence:online"  # ZSET：member=用户 JSON，score=过期时间（毫秒）
PRESENCE_TTL = int(os.getenv("PRESENCE_TTL", "90"))  # 秒；进程被杀后最多这么久自动下线
PRESENCE_HEARTBEAT_TIMEOUT = int(os.getenv("PRESENCE_HEARTBEAT_TIMEOUT", "120"))

# 即时聊天
CHAT_GATEWAY_ID = os.getenv("CHAT_GATEWAY_ID", "gw1")  # 单进程部署只有一个网关
CHAT_ONLINE_TTL = int(os.getenv("CHAT_ONLINE_TTL", "90"))  # 在线状态 TTL（秒），心跳续期
CHAT_ONLINE_KEY = "chat:online:{uid}"
CHAT_SEQ_KEY = "chat:seq:{conv_id}"
CHAT_MAX_BODY = int(os.getenv("CHAT_MAX_BODY", "4000"))
CHAT_HISTORY_LIMIT = int(os.getenv("CHAT_HISTORY_LIMIT", "500"))
CHAT_HEARTBEAT_TIMEOUT = int(os.getenv("CHAT_HEARTBEAT_TIMEOUT", "120"))  # 服务端兜底断连
CHAT_RATE_LIMIT = int(os.getenv("CHAT_RATE_LIMIT", "10"))  # 每 5 秒最多消息数
CHAT_RATE_WINDOW = 5.0
