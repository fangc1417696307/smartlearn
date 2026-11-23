import json
import re
import urllib.request
import urllib.error

BASE = "http://127.0.0.1:8001/api"


def req(path, method="GET", data=None, token=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    body = json.dumps(data).encode() if data is not None else None
    r = urllib.request.Request(BASE + path, data=body, headers=headers, method=method)
    try:
        resp = urllib.request.urlopen(r)
        return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


def get_captcha():
    _, cap = req("/auth/captcha")
    m = re.match(r"(\d+)\s*([+\-*])\s*(\d+)", cap["question"])
    a, op, b = int(m.group(1)), m.group(2), int(m.group(3))
    ans = {"+": a + b, "-": a - b, "*": a * b}[op]
    return cap["captcha_id"], str(ans)


print("=== 1. 登录管理员（算数验证码 + 密码） ===")
cid, ans = get_captcha()
st, r = req("/auth/login", "POST", {"account": "admin", "password": "admin123", "captcha_id": cid, "captcha_answer": ans})
print(f"  状态={st} must_change={r.get('user', {}).get('must_change_password')} roles={[x['code'] for x in r.get('user', {}).get('roles', [])]} perms={len(r.get('permissions', []))}")
token = r.get("access_token")

print("=== 2. 强制改密 ===")
st, r = req("/auth/change-password", "POST", {"old_password": "admin123", "new_password": "Admin@2026"}, token)
print(f"  状态={st} {r}")

print("=== 3. 用新密码重新登录 ===")
cid, ans = get_captcha()
st, r = req("/auth/login", "POST", {"account": "admin", "password": "Admin@2026", "captcha_id": cid, "captcha_answer": ans})
print(f"  状态={st} must_change={r.get('user', {}).get('must_change_password')}")
token = r.get("access_token")

print("=== 4. 管理员访问用户列表（RBAC 有权限） ===")
st, r = req("/users/", token=token)
print(f"  状态={st} 用户数={len(r) if isinstance(r, list) else r}")

print("=== 5. 注册学生（算数验证码） ===")
cid, ans = get_captcha()
st, r = req("/auth/register", "POST", {"account": "stu001", "password": "stu123456", "nickname": "测试学生", "major": "计算机", "captcha_id": cid, "captcha_answer": ans})
print(f"  状态={st} 账号={r.get('user', {}).get('account')} roles={[x['code'] for x in r.get('user', {}).get('roles', [])]}")
stu_token = r.get("access_token")

print("=== 6. 学生访问用户列表（RBAC 应 403） ===")
st, r = req("/users/", token=stu_token)
print(f"  状态={st} 详情={r}")

print("=== 7. 算数验证码错误应被拒绝 ===")
cid, _ = get_captcha()
st, r = req("/auth/login", "POST", {"account": "admin", "password": "Admin@2026", "captcha_id": cid, "captcha_answer": "99999"})
print(f"  状态={st} 详情={r}")

print("=== 8. 发送邮箱验证码（降级：打印到后端日志） ===")
st, r = req("/auth/send-code", "POST", {"email": "admin@smartlearn.edu"})
print(f"  状态={st} {r}")
