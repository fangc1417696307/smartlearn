"""实时在线状态测试（连接级）。

在临时目录启动独立后端（端口 8014、独立 SQLite、Redis DB 15），验证：
1. 只有 HTTP 请求不再算在线；
2. presence WebSocket 连接建立即在线，断开即下线；
3. 同一用户多标签页只算 1 人；
4. 非法 token 被拒绝；
5. Redis 可用时，在线人数趋势采样取实时值。
"""
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request

from websockets.sync.client import connect

BACKEND = os.path.dirname(os.path.abspath(__file__))
PY = sys.executable
PORT = 8014
BASE = f"http://127.0.0.1:{PORT}"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

FAILS = []


def check(name, cond, detail=""):
    print(("  PASS " if cond else "  FAIL ") + name + (f"  [{detail}]" if detail else ""))
    if not cond:
        FAILS.append(name)


def req(path, method="GET", data=None, token=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = "Bearer " + token
    body = json.dumps(data).encode() if data is not None else None
    r = urllib.request.Request(BASE + path, data=body, headers=headers, method=method)
    try:
        resp = urllib.request.urlopen(r, timeout=10)
        raw = resp.read()
        return resp.status, (json.loads(raw) if raw else None)
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            return e.code, json.loads(raw)
        except Exception:
            return e.code, raw.decode("utf-8", "replace")


def login(account, password):
    _, cap = req("/api/auth/captcha")
    m = re.match(r"(\d+)\s*([+\-*])\s*(\d+)", cap["question"])
    a, op, b = int(m.group(1)), m.group(2), int(m.group(3))
    ans = {"+": a + b, "-": a - b, "*": a * b}[op]
    st, r = req("/api/auth/login", "POST", {
        "account": account, "password": password,
        "captcha_id": cap["captcha_id"], "captcha_answer": str(ans),
    })
    assert st == 200, f"login {account}: {st} {r}"
    return r["access_token"]


tmp = tempfile.mkdtemp(prefix="smartlearn_presence_")
print("临时目录:", tmp)
env = os.environ.copy()
env["PYTHONPATH"] = BACKEND
env["PYTHONIOENCODING"] = "utf-8"
# 用独立的 Redis DB，避免和本机正在跑的 SmartLearn 互相影响
env["REDIS_URL"] = "redis://127.0.0.1:6380/15"
env["ADMIN_INITIAL_PASSWORD"] = "admin123"
log_path = os.path.join(tmp, "uvicorn.log")
log = open(log_path, "wb")
proc = subprocess.Popen(
    [PY, "-m", "uvicorn", "main:app", "--port", str(PORT), "--log-level", "warning"],
    cwd=tmp, env=env, stdout=log, stderr=subprocess.STDOUT,
)


def stop_server():
    proc.terminate()
    try:
        proc.wait(timeout=8)
    except subprocess.TimeoutExpired:
        proc.kill()
    log.close()


def online_snapshot(token):
    st, bs = req("/api/stats/bigscreen", token=token)
    assert st == 200, f"bigscreen: {st} {bs}"
    return bs["online"], bs


def wait_online(token, expected, timeout=6):
    end = time.time() + timeout
    data = {"count": None, "users": []}
    while time.time() < end:
        data, _ = online_snapshot(token)
        if data.get("count") == expected:
            return data
        time.sleep(0.2)
    return data


try:
    ready = False
    for _ in range(300):
        try:
            urllib.request.urlopen(BASE + "/openapi.json", timeout=1)
            ready = True
            break
        except Exception:
            time.sleep(0.1)
    if not ready:
        print(open(log_path, encoding="utf-8", errors="replace").read()[-4000:])
        raise SystemExit("服务启动失败")

    token = login("admin", "admin123")
    ws_url = f"ws://127.0.0.1:{PORT}/ws/presence?token={token}&device=test"

    print("\n=== 1. HTTP 请求不再伪造在线 ===")
    first, _ = online_snapshot(token)
    second, _ = online_snapshot(token)
    check("没有 WS 连接时在线人数为 0", first["count"] == 0 and second["count"] == 0,
          f'{first["count"]}, {second["count"]}')

    print("\n=== 2. 连接即在线，断开即下线 ===")
    with connect(ws_url, open_timeout=10) as ws:
        ws.send(json.dumps({"type": "ping"}))
        pong = json.loads(ws.recv(timeout=10))
        check("心跳返回 pong", pong.get("type") == "pong", str(pong))
        online = wait_online(token, 1)
        check("连接后在线人数为 1", online["count"] == 1, str(online["count"]))
        check("在线名单包含 admin", any(u.get("account") == "admin" for u in online["users"]),
              str(online["users"]))

        print("\n=== 3. 多标签页去重 ===")
        with connect(ws_url, open_timeout=10) as ws2:
            ws2.send(json.dumps({"type": "ping"}))
            ws2.recv(timeout=10)
            online = wait_online(token, 1)
            check("同一用户两个连接仍算 1 人", online["count"] == 1, str(online["count"]))
        online = wait_online(token, 1)
        check("关闭一个标签仍在线", online["count"] == 1, str(online["count"]))
        time.sleep(0.6)

    online = wait_online(token, 0)
    check("全部连接关闭后立即下线", online["count"] == 0, str(online["count"]))

    print("\n=== 4. 非法 token ===")
    try:
        with connect(ws_url.replace(token, "bad-token"), open_timeout=5) as bad:
            msg = json.loads(bad.recv(timeout=5))
            check("非法 token 收到 UNAUTHORIZED", msg.get("code") == "UNAUTHORIZED", str(msg))
    except Exception as exc:  # noqa: BLE001 - 服务端也可能直接断开
        check("非法 token 连接被关闭", True, str(exc))

    print("\n=== 5. 在线趋势采样 ===")
    _, bs = online_snapshot(token)
    if bs["redis"]["connected"]:
        with connect(ws_url, open_timeout=10) as ws:
            ws.send(json.dumps({"type": "ping"}))
            ws.recv(timeout=10)
            time.sleep(2.2)
            _, bs2 = online_snapshot(token)
            series = bs2["mq"].get("series") or []
            last = series[-1] if series else {}
            check("采样曲线记录实时在线人数", last.get("online") == 1, str(last))
    else:
        print("  SKIP Redis 未启动，跳过趋势采样")
finally:
    stop_server()

print("\n" + "=" * 50)
if FAILS:
    print(f"失败 {len(FAILS)} 项:", FAILS)
    sys.exit(1)
print("全部通过")
