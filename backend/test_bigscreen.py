"""数据大屏链路测试（需先启动后端与 Redis）。

覆盖：
1. 管理员登录
2. 大屏接口返回 Redis / 消息队列指标
3. 投递模拟事件后，消费者确实消费到消息
"""
import json
import re
import time
import urllib.error
import urllib.request

BASE = "http://127.0.0.1:8001/api"


def req(path, method="GET", data=None, token=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    body = json.dumps(data).encode() if data is not None else None
    r = urllib.request.Request(BASE + path, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(r) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


def get_captcha():
    _, cap = req("/auth/captcha")
    m = re.match(r"(\d+)\s*([+\-*])\s*(\d+)", cap["question"])
    a, op, b = int(m.group(1)), m.group(2), int(m.group(3))
    ans = {"+": a + b, "-": a - b, "*": a * b}[op]
    return cap["captcha_id"], str(ans)


def login(password):
    cid, ans = get_captcha()
    return req("/auth/login", "POST", {
        "account": "admin", "password": password,
        "captcha_id": cid, "captcha_answer": ans,
    })


checks = []


def check(name, ok, detail=""):
    checks.append(ok)
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f"  {detail}" if detail else ""))


print("=== 1. 管理员登录 ===")
st, r = login("123456")
if st != 200:
    st, r = login("admin123")
token = r.get("access_token") if st == 200 else None
check("登录成功", bool(token), f"status={st}")
if not token:
    print("无法继续，请确认 admin 密码（默认 123456 / admin123）")
    raise SystemExit(1)

print("=== 2. 大屏接口 ===")
st, bs = req("/stats/bigscreen", token=token)
check("接口 200", st == 200)
check("Redis 已连接", bs["redis"]["connected"], f"version={bs['redis'].get('version')}")
check("消息队列已连接", bs["mq"]["connected"],
      f"topic={bs['mq'].get('topic')} partitions={bs['mq'].get('partitions')}")
check("包含业务数据", "total_users" in bs["overview"], f"total_users={bs['overview']['total_users']}")
check("包含在线用户", "count" in bs["online"], f"online={bs['online']['count']}")

print("=== 3. 投递模拟事件 ===")
before = bs["mq"]["consumed"]
st, demo = req("/stats/demo-events?count=5", "POST", token=token)
check("投递成功", st == 200 and demo.get("produced") == 5, f"produced={demo.get('produced')}")

time.sleep(2)
st, bs2 = req("/stats/bigscreen", token=token)
check("消费者已消费", bs2["mq"]["consumed"] >= before + 5,
      f"before={before} after={bs2['mq']['consumed']}")
check("事件流非空", len(bs2["events"]) > 0, f"events={len(bs2['events'])}")
check("吞吐曲线有数据", len(bs2["mq"]["series"]) > 0, f"samples={len(bs2['mq']['series'])}")
check("缓存产生了命中/未命中", bs2["redis"]["cache"]["total"] > 0,
      f"hit_rate={bs2['redis']['cache']['hit_rate']}%")

passed = sum(1 for c in checks if c)
print(f"\n结果：{passed}/{len(checks)} 通过")
raise SystemExit(0 if passed == len(checks) else 1)
