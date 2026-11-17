# SmartLearn

个性化学习多智能体系统。前后端分离，集成 **Redis 缓存** 与 **Kafka 消息队列**，管理员界面提供实时数据大屏。

- `backend/`：FastAPI + SQLite + Redis + Kafka
- `frontend/`：Vue 3 + Vite + Element Plus + ECharts
- `prototype/`：早期纯前端原型（已由 `frontend/` 取代）
- `docs/`：需求与 PRD
- `scripts/`：Windows 启动脚本
- `backend/tools/`：Redis 与 Kafka 本地运行时（体积大，未入库，新机器需自行下载）

## 一键启动（推荐）

双击项目根目录的 **`start-all.bat`**，会依次打开：

1. Redis（`127.0.0.1:6380`）
2. Kafka（`127.0.0.1:9092`）
3. 后端（`127.0.0.1:8001`）
4. 前端（`127.0.0.1:5173`）

最后自动打开浏览器。关闭对应的服务窗口即可停止。

> Kafka 首次启动约需 15 秒；后端会自动重试连接，不需要手动等待。
> 需要本机有 Java 17+，本项目使用 `D:\develop\JDK`（Java 25），可在
> `scripts/start-kafka.bat` 里修改 `JAVA_HOME`。

## 手动启动

需要四个终端。

### 1. Redis（6380）

```bash
cd backend/tools/redis
redis-server.exe --port 6380 --bind 127.0.0.1 --save "" --appendonly no
```

或双击 `scripts/start-redis.bat`。

> 本机 6379 端口是禅道自带的 Redis 服务（需要密码），本项目使用独立的 **6380** 实例，互不影响。

### 2. Kafka（9092）

```bash
scripts\start-kafka.bat
```

或直接运行：

```bash
cd backend/tools/kafka/kafka_2.13-4.4.0
set JAVA_HOME=D:\develop\JDK
bin\windows\kafka-server-start.bat config\server.properties
```

Kafka 4.4.0（KRaft 模式，单节点）放在 `backend/tools/kafka`，**不需要 Docker**。

> `backend/tools/` 下的 Kafka/Redis 二进制与 Kafka 数据目录超过 1GB，已通过 `.gitignore` 排除，不随仓库分发。
> 新机器上请先下载 Kafka 4.4.0 解压到 `backend/tools/kafka/kafka_2.13-4.4.0`，并将 Redis for Windows 放入 `backend/tools/redis`，再运行启动脚本。

### 3. 后端（8001）

```bash
cd backend
venv/Scripts/python -m uvicorn main:app --port 8001
```

或双击 `scripts/start-backend.bat`。

- 后端地址：http://127.0.0.1:8001
- 接口文档：http://127.0.0.1:8001/docs
- 注意：本机 8000 端口被 C-Lodop 占用，必须用 **8001**。

首次在新机器上运行，先安装依赖：

```bash
cd backend
python -m venv venv
venv/Scripts/python -m pip install -r requirements.txt
```

### 4. 前端（5173）

```bash
cd frontend
npm install   # 首次运行
npm run dev
```

或双击 `scripts/start-frontend.bat`，然后打开 http://127.0.0.1:5173 。

## 数据大屏（Redis + Kafka）

管理员登录后，左侧菜单进入 **「数据大屏」**（路由 `/stats`）。

大屏每 2 秒刷新，展示：

| 模块 | 内容 | 用到的技术 |
| --- | --- | --- |
| KPI 卡片 | 总用户、在线用户、今日新增、消息吞吐、缓存命中率、消息积压 | SQLite + Redis + Kafka |
| Redis 缓存层 | 应用缓存命中率仪表盘、内存占用、Key 数量、OPS、客户端数 | Redis `INFO` / `DBSIZE` |
| 消息队列 | 生产/消费速率曲线、累计生产/消费、Topic 积压、消费者 Lag | Kafka |
| 实时事件流 | 登录、注册、建号、资源生成、答疑、测评等事件 | Kafka |
| 业务图表 | 角色分布、近 7 天新增、在线人数趋势 | SQLite + Redis |

### 技术链路

```
业务事件（登录/注册/资源生成/答疑）
        │
        ▼
Kafka  PRODUCE → smartlearn.events（3 分区）
        │
        ▼
消费者组 bigscreen  POLL + COMMIT OFFSET
        │
        ▼
前端大屏  每 2 秒轮询 /api/stats/bigscreen
```

- **缓存**：`/api/stats/overview` 的聚合结果写入 Redis，TTL 5 秒；大屏统计真实的应用缓存命中率。
- **消息队列**：登录、注册、用户增删改、教师审核等操作都会 `produce` 到 Kafka topic `smartlearn.events`；后台消费者组 `bigscreen` 消费并提交 offset。
- **Kafka 指标**：Topic 积压 = 各分区 `log-end-offset - log-start-offset` 之和；消费者 Lag = 各分区 `log-end-offset - committed-offset` 之和；分区数、消费者数通过 AdminClient 读取。
- **在线用户**：每次带 token 的请求都会刷新 Redis Sorted Set 中的活跃时间，5 分钟无请求视为离线。
- **演示按钮**：大屏右上角「模拟活动」会向 Kafka 投递 8 条模拟事件，方便答辩演示；对应接口 `POST /api/stats/demo-events`。
- **降级**：Kafka 没启动时，系统业务功能照常使用，大屏显示「MQ 未连接」，不会报错崩溃。

相关代码：

- `backend/mq.py`：Kafka 生产者、消费者组、指标快照
- `backend/redis_client.py`：Redis 连接、缓存、在线用户、服务指标
- `backend/routers/stats.py`：`/stats/bigscreen`、`/stats/demo-events`
- `frontend/src/views/Stats.vue`：数据大屏页面

Redis 与 Kafka 连接可通过 `backend/.env` 修改：

```
REDIS_URL=redis://127.0.0.1:6380/0
KAFKA_BOOTSTRAP_SERVERS=127.0.0.1:9092
```

### Kafka 运行说明

- 版本：Apache Kafka 4.4.0，单节点 KRaft（不需要 ZooKeeper）。
- 数据目录：`backend/tools/kafka/data`。
- Topic：`smartlearn.events`，3 个分区，自动创建。
- 消费者组：`bigscreen`。
- **Windows 脚本补丁**：Kafka 自带的 `bin/windows/kafka-run-class.bat` 会把所有 jar 拼进命令行，超过 Windows 8191 字符限制。项目已把它改成 Java 通配符 classpath：

  ```bat
  set CLASSPATH=%BASE_DIR%\libs\*
  ```

  如果重新下载 Kafka，需要重新应用这处修改。
- Kafka 进程需要保持运行；关闭 `start-kafka.bat` 窗口即停止。

## 常见启动错误

| 现象 | 原因 | 解决 |
| --- | --- | --- |
| `npm error Missing script: "dev"` | 在项目根目录执行了 npm | 先 `cd frontend` |
| `ModuleNotFoundError: No module named 'database'` | 在项目根目录启动 uvicorn | 先 `cd backend` 再执行 uvicorn |
| `ModuleNotFoundError: No module named 'fastapi'` / `'dotenv'` / `'redis'` / `'confluent_kafka'` | 没用虚拟环境 | 用 `venv/Scripts/python`，或先装 `requirements.txt` |
| 命令执行后直接退出、没有任何输出 | 执行了 `python main.py` | 用 `uvicorn main:app --port 8001` 启动 |
| 数据大屏显示 Redis 未连接 | Redis 没启动或端口不对 | 运行 `scripts/start-redis.bat`，确认 6380 可用 |
| 数据大屏显示 MQ 未连接 | Kafka 没启动或还在启动中 | 运行 `scripts/start-kafka.bat`，确认 9092 可用 |
| Kafka 窗口报 `JAVA_HOME` 找不到 | Java 路径不对 | 修改 `scripts/start-kafka.bat` 里的 `JAVA_HOME` |
| Kafka 窗口报「输入行太长」 | 没应用 `kafka-run-class.bat` 的 classpath 补丁 | 按上面的 Kafka 运行说明修改 |
| `address already in use` | 端口被占用 | 结束占用 8001/6380/9092 的进程 |

## 演示账号

- 管理员：`admin` / `123456`（以当前 `backend/smartlearn.db` 实际数据为准）
- 老师：`teacher01` / `teacher123`
- 学生：`student01` / `student123`

> 删除 `backend/smartlearn.db` 后重启后端会重新建库；此时管理员密码为 `.env` 中的
> `ADMIN_INITIAL_PASSWORD`（默认 `admin123`），且需首次登录改密。
