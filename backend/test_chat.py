"""SmartLearn 聊天功能端到端测试。

在临时目录启动真实 uvicorn（独立的 smartlearn.db），用 urllib 调 REST、
用最小 WebSocket 客户端测长连接，覆盖：收发、ACK、去重、seq、成员校验、
心跳、在线状态、离线同步。
"""
import base64
import json
import os
import socket
import sqlite3
import struct
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request

BACKEND = os.path.dirname(os.path.abspath(__file__))
PY = sys.executable
PORT = 8013
BASE = f"http://127.0.0.1:{PORT}"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

FAILS = []


def check(name, cond, detail=""):
    print(("  PASS " if cond else "  FAIL ") + name + (f"  [{detail}]" if detail else ""))
    if not cond:
        FAILS.append(name)


# ---------------------------------------------------------------------------
# HTTP
# ---------------------------------------------------------------------------

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
    q = cap["question"]
    import re
    m = re.match(r"(\d+)\s*([+\-*])\s*(\d+)", q)
    a, op, b = int(m.group(1)), m.group(2), int(m.group(3))
    ans = {"+": a + b, "-": a - b, "*": a * b}[op]
    st, r = req("/api/auth/login", "POST", {
        "account": account, "password": password,
        "captcha_id": cap["captcha_id"], "captcha_answer": str(ans),
    })
    assert st == 200, f"login {account} failed: {st} {r}"
    return r["access_token"], r["user"]


# ---------------------------------------------------------------------------
# 最小 WebSocket 客户端
# ---------------------------------------------------------------------------

class WSClosed(Exception):
    pass


class WS:
    def __init__(self, path, timeout=5.0):
        self.sock = socket.create_connection(("127.0.0.1", PORT), timeout=timeout)
        key = base64.b64encode(os.urandom(16)).decode()
        handshake = (
            f"GET {path} HTTP/1.1\r\n"
            f"Host: 127.0.0.1:{PORT}\r\n"
            "Upgrade: websocket\r\nConnection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n"
        )
        self.sock.sendall(handshake.encode())
        resp = b""
        while b"\r\n\r\n" not in resp:
            chunk = self.sock.recv(4096)
            if not chunk:
                raise WSClosed("handshake closed")
            resp += chunk
        status_line = resp.split(b"\r\n", 1)[0]
        if b"101" not in status_line:
            raise WSClosed(status_line.decode("latin1"))

    def send(self, obj):
        data = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        header = bytearray([0x81])
        mask = os.urandom(4)
        n = len(data)
        if n < 126:
            header.append(0x80 | n)
        elif n < 65536:
            header.append(0x80 | 126)
            header += struct.pack("!H", n)
        else:
            header.append(0x80 | 127)
            header += struct.pack("!Q", n)
        header += mask
        masked = bytes(b ^ mask[i % 4] for i, b in enumerate(data))
        self.sock.sendall(bytes(header) + masked)

    def _read_exact(self, n):
        buf = b""
        while len(buf) < n:
            chunk = self.sock.recv(n - len(buf))
            if not chunk:
                raise WSClosed("eof")
            buf += chunk
        return buf

    def recv_raw(self):
        b1, b2 = self._read_exact(2)
        opcode = b1 & 0x0F
        length = b2 & 0x7F
        if length == 126:
            length = struct.unpack("!H", self._read_exact(2))[0]
        elif length == 127:
            length = struct.unpack("!Q", self._read_exact(8))[0]
        masked = b2 & 0x80
        mask = self._read_exact(4) if masked else b""
        data = self._read_exact(length)
        if masked:
            data = bytes(b ^ mask[i % 4] for i, b in enumerate(data))
        if opcode == 0x8:
            raise WSClosed(f"close frame {struct.unpack('!H', data[:2])[0] if len(data) >= 2 else ''}")
        if opcode == 0x9:  # ping -> pong
            self.sock.sendall(b"\x8a\x80" + os.urandom(4))
            return self.recv_raw()
        return data.decode("utf-8")

    def recv(self):
        return json.loads(self.recv_raw())

    def recv_until(self, wanted, timeout=5.0, limit=30):
        """读到指定类型的消息；其它事件（presence/pong）跳过并返回收集箱。"""
        self.sock.settimeout(timeout)
        seen = []
        for _ in range(limit):
            data = self.recv()
            if data.get("type") == wanted:
                return data, seen
            seen.append(data)
        raise AssertionError(f"没有等到 {wanted}，收到 {seen}")

    def expect_silence(self, seconds=0.6):
        self.sock.settimeout(seconds)
        start = time.time()
        try:
            while time.time() - start < seconds:
                data = self.recv()
                if data.get("type") == "chat":
                    return data
        except (socket.timeout, TimeoutError):
            return None
        except WSClosed:
            return None
        return None

    def close(self):
        try:
            self.sock.sendall(b"\x88\x80" + os.urandom(4))
        except Exception:
            pass
        try:
            self.sock.close()
        except Exception:
            pass


# ---------------------------------------------------------------------------
# 启动服务
# ---------------------------------------------------------------------------

tmp = tempfile.mkdtemp(prefix="smartlearn_chat_it_")
print("临时目录:", tmp)
env = os.environ.copy()
env["PYTHONPATH"] = BACKEND
env["PYTHONIOENCODING"] = "utf-8"
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

    print("\n=== 1. 登录并拉取演示会话 ===")
    s_token, s_user = login("student01", "student123")
    t_token, t_user = login("teacher01", "teacher123")
    st, convs = req("/api/chat/conversations", token=s_token)
    check("会话列表 200", st == 200, str(st))
    private = next((c for c in convs if c["type"] == "private"), None)
    group = next((c for c in convs if c["type"] == "group"), None)
    check("存在演示私聊", private is not None)
    check("存在演示课程群", group is not None)
    check("私聊未读数 > 0", private and private["unread"] > 0, str(private and private["unread"]))
    check("私聊对方是演示老师", private and private["peer"]["account"] == "teacher01")
    print("  会话:", [(c["name"], c["type"], c["unread"]) for c in convs])

    print("\n=== 2. WebSocket 连接 + 心跳 + 在线状态 ===")
    sws = WS(f"/ws/chat?token={s_token}&device=web")
    sws.send({"type": "ping"})
    pong, _ = sws.recv_until("pong")
    check("ping -> pong", pong["type"] == "pong")

    tws = WS(f"/ws/chat?token={t_token}&device=web")
    ev, _ = sws.recv_until("presence")
    check("老师上线，学生收到 presence", ev["userId"] == t_user["id"] and ev["online"] is True, str(ev))

    print("\n=== 3. 发送 + ACK + 投递 + seq ===")
    before = private["lastSeq"]
    sws.send({"type": "chat", "convId": private["id"], "clientId": "it-1", "body": "端到端测试消息 A"})
    ack, _ = sws.recv_until("ack")
    check("发送方收到 ack", ack["clientId"] == "it-1" and ack["duplicate"] is False, str(ack))
    check("seq 连续递增", ack["seq"] == before + 1, f'{before} -> {ack["seq"]}')
    chat, _ = tws.recv_until("chat")
    check("接收方收到 chat", chat["message"]["body"] == "端到端测试消息 A")
    check("接收方消息 clientId 一致", chat["message"]["clientId"] == "it-1")
    check("接收方 seq 与 ack 一致", chat["message"]["seq"] == ack["seq"])

    print("\n=== 4. 幂等去重（P10） ===")
    sws.send({"type": "chat", "convId": private["id"], "clientId": "it-1", "body": "端到端测试消息 A"})
    ack2, _ = sws.recv_until("ack")
    check("重复消息 ack.duplicate=true", ack2["duplicate"] is True, str(ack2))
    check("重复消息 seq 不变", ack2["seq"] == ack["seq"])
    late = tws.expect_silence(0.8)
    check("重复消息没有二次投递", late is None, str(late))

    print("\n=== 5. 双向收发 + 历史顺序（P11） ===")
    tws.send({"type": "chat", "convId": private["id"], "clientId": "it-t1", "body": "老师回复测试"})
    tack, _ = tws.recv_until("ack")
    got, _ = sws.recv_until("chat")
    check("学生收到老师消息", got["message"]["body"] == "老师回复测试")
    st, hist = req(f"/api/chat/conversations/{private['id']}/messages?afterSeq={before}", token=s_token)
    seqs = [m["seq"] for m in hist["messages"]]
    check("历史接口 200", st == 200)
    check("增量消息 seq 严格递增", seqs == sorted(seqs) and len(seqs) == 2, str(seqs))
    check("增量不包含旧消息", all(x > before for x in seqs))

    print("\n=== 6. 群聊投递（P14） ===")
    sws.send({"type": "chat", "convId": group["id"], "clientId": "it-g1", "body": "群消息测试"})
    gack, _ = sws.recv_until("ack")
    gchat, _ = tws.recv_until("chat")
    check("群聊 ack", gack["duplicate"] is False)
    check("群成员收到群消息", gchat["message"]["convId"] == group["id"])

    print("\n=== 7. 消息级权限（P16） ===")
    _, cap = req("/api/auth/captcha")
    import re
    m = re.match(r"(\d+)\s*([+\-*])\s*(\d+)", cap["question"])
    a, op, b = int(m.group(1)), m.group(2), int(m.group(3))
    ans = {"+": a + b, "-": a - b, "*": a * b}[op]
    st, reg = req("/api/auth/register", "POST", {
        "account": "out_chat", "password": "out123456", "nickname": "外人",
        "major": "测试", "role": "student",
        "captcha_id": cap["captcha_id"], "captcha_answer": str(ans),
    })
    check("注册外部学生", st == 200, str(st))
    outsider_id = reg["user"]["id"]
    st, odd = req("/api/chat/conversations", "POST",
                  {"type": "private", "peerId": outsider_id}, token=t_token)
    check("老师与外人建会话", st == 200, str(st))
    sws.send({"type": "chat", "convId": odd["id"], "clientId": "it-x1", "body": "越权消息"})
    err, _ = sws.recv_until("error")
    check("非成员发送被拒 NOT_MEMBER", err["code"] == "NOT_MEMBER", str(err))

    print("\n=== 8. 已读游标 ===")
    st, convs2 = req("/api/chat/conversations", token=s_token)
    p2 = next(c for c in convs2 if c["id"] == private["id"])
    check("未读数 > 0", p2["unread"] > 0, str(p2["unread"]))
    st, rd = req(f"/api/chat/conversations/{private['id']}/read", "POST", {"seq": 999999}, token=s_token)
    check("已读上报 200", st == 200, str(st))
    st, convs3 = req("/api/chat/conversations", token=s_token)
    p3 = next(c for c in convs3 if c["id"] == private["id"])
    check("已读后未读数归零", p3["unread"] == 0, str(p3["unread"]))
    check("已读被夹紧到最大 seq", rd["lastReadSeq"] == p2["lastSeq"], f'{rd["lastReadSeq"]} vs {p2["lastSeq"]}')

    print("\n=== 9. 离线消息与重连同步（P12） ===")
    tws.close()
    time.sleep(0.4)
    offline_msg = "老师离线期间的消息"
    sws.send({"type": "chat", "convId": private["id"], "clientId": "it-off1", "body": offline_msg})
    oack, _ = sws.recv_until("ack")
    st, convs4 = req("/api/chat/conversations", token=t_token)
    tconv = next(c for c in convs4 if c["id"] == private["id"])
    tws2 = WS(f"/ws/chat?token={t_token}&device=web")
    st, sync = req(
        f"/api/chat/conversations/{private['id']}/messages?afterSeq={tconv['lastSeq'] - 1}",
        token=t_token,
    )
    check("离线消息已落库", any(m["body"] == offline_msg for m in sync["messages"]))
    check("同步 seq 从游标之后开始", all(m["seq"] > tconv["lastSeq"] - 1 for m in sync["messages"]))
    check("离线消息 seq 正确", any(m["seq"] == oack["seq"] for m in sync["messages"]))

    print("\n=== 10. 无 token 连接被拒（P16） ===")
    bad = WS("/ws/chat?token=bad-token")
    try:
        msg = bad.recv()
        check("非法 token 收到 UNAUTHORIZED", msg.get("code") == "UNAUTHORIZED", str(msg))
    except WSClosed as exc:
        check("非法 token 连接被关闭", True, str(exc))
    finally:
        bad.close()

    print("\n=== 11. Redis 降级不影响聊天接口 ===")
    st, _ = req("/api/chat/conversations", token=s_token)
    check("Redis 不可用时 REST 仍可用", st == 200, str(st))

    tws2.close()
    sws.close()
    time.sleep(0.3)
finally:
    stop_server()

print("\n" + "=" * 50)
if FAILS:
    print(f"失败 {len(FAILS)} 项:", FAILS)
    sys.exit(1)
print("全部通过")
