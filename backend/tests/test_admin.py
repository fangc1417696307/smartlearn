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
    return cap["captcha_id"], str({"+" : a + b, "-": a - b, "*": a * b}[op])


# 登录管理员（兼容初始密码或已改密）
def login_admin():
    for pwd in ["admin123", "Admin@2026"]:
        cid, ans = get_captcha()
        st, r = req("/auth/login", "POST", {"account": "admin", "password": pwd, "captcha_id": cid, "captcha_answer": ans})
        if st == 200:
            return st, r, pwd
    return None, {}, None

st, r, pwd = login_admin()
if st != 200:
    print("[登录失败]", r)
    raise SystemExit(1)
if r.get("user", {}).get("must_change_password"):
    req("/auth/change-password", "POST", {"old_password": pwd, "new_password": "Admin@2026"}, r["access_token"])
    st, r, pwd = login_admin()
token = r["access_token"]
print(f"[登录] 状态={st} 角色={[x['code'] for x in r['user']['roles']]}")

print("\n=== 用户管理 CRUD ===")
st, users = req("/users/", token=token)
print(f"  列表用户数={len(users)}")

st, r = req("/users/", "POST", {"account": "stu100", "password": "pass123456", "nickname": "张三", "major": "数学", "role_ids": [1]}, token)
print(f"  新增用户状态={st} id={r.get('id')}")
uid = r.get("id")

st, r = req(f"/users/{uid}", "PUT", {"nickname": "张三改", "major": "应用数学", "role_ids": [1, 2]}, token)
print(f"  更新用户状态={st} 角色数={len(r.get('roles', []))}")

st, r = req(f"/users/{uid}", "DELETE", token=token)
print(f"  删除用户状态={st}")

print("\n=== 角色管理 CRUD ===")
st, roles = req("/roles/", token=token)
print(f"  角色列表={[(x['code'], len(x['permissions'])) for x in roles]}")

st, perms = req("/roles/permissions", token=token)
perm_ids = [p["id"] for p in perms[:3]]
st, r = req("/roles/", "POST", {"name": "助教", "code": "assistant", "description": "协助老师", "permission_ids": perm_ids}, token)
print(f"  新建角色状态={st} id={r.get('id')} 权限数={len(r.get('permissions', []))}")
rid = r.get("id")

st, r = req(f"/roles/{rid}", "PUT", {"name": "助教2", "permission_ids": perm_ids + [perms[3]["id"]]}, token)
print(f"  更新角色状态={st} 权限数={len(r.get('permissions', []))}")

st, r = req(f"/roles/{rid}", "DELETE", token=token)
print(f"  删除角色状态={st}")

print("\n=== 学生访问管理接口应 403 ===")
cid, ans = get_captcha()
st, r = req("/auth/register", "POST", {"account": "stu200", "password": "stu123456", "nickname": "李四", "major": "英语", "captcha_id": cid, "captcha_answer": ans})
stu_token = r.get("access_token")
st, r = req("/users/", token=stu_token)
print(f"  学生访问用户列表状态={st} {r.get('detail')}")
