# 测试脚本

这里存放的是**手动验证脚本**（不是 pytest 用例），运行后逐项打印 `PASS / FAIL`，有失败时进程退出码非 0。

## 自启动（推荐，无需先开服务）

这两个脚本会在临时目录启动独立后端和独立 SQLite，不会动项目数据库，也不会占用 8001：

| 脚本 | 端口 | 覆盖内容 |
| --- | --- | --- |
| `test_chat.py` | 8013 | 聊天收发、ACK、去重、seq、群聊、成员校验、已读、离线同步 |
| `test_presence.py` | 8014 | 连接级实时在线、多标签去重、断开即下线、在线趋势采样 |

```bash
cd backend
venv/Scripts/python tests/test_chat.py
venv/Scripts/python tests/test_presence.py
```

Windows 下也可以双击 `run_offline_tests.bat`，一次跑完上面两个。

> `test_presence.py` 会使用 Redis DB 15（如果 6380 上的 Redis 已启动）；Redis 没启动时自动退回进程内在线表，测试仍然可跑。

## 需要先启动后端（8001）

以下脚本直接请求 `http://127.0.0.1:8001`，运行前先启动后端：

| 脚本 | 说明 |
| --- | --- |
| `test_api.py` | 登录、注册、RBAC、验证码等基础接口；**会修改数据**（注册测试账号、修改管理员密码） |
| `test_admin.py` | 管理员用户/角色管理接口 |
| `test_bigscreen.py` | 数据大屏 Redis / Kafka 链路；需要 Redis 与 Kafka 已启动，且管理员密码正确 |

```bash
cd backend
venv/Scripts/python tests/test_api.py
```

建议只在临时数据库或确认可以改动的环境里运行这些「需预启动」的脚本。
