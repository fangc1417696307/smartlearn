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
ONLINE_KEY = "stats:online"
ONLINE_WINDOW_MS = 5 * 60 * 1000  # 5 分钟内活跃视为在线
CACHE_OVERVIEW_KEY = "stats:cache:overview"
CACHE_OVERVIEW_TTL = 5  # 秒
