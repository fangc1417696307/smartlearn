import random
import time
import uuid

# 内存存储（单进程可用，期末作品量级足够）
_arith = {}   # captcha_id -> {answer, expire}
_codes = {}   # email -> {code, expire}

ARITH_TTL = 300      # 算数验证码 5 分钟
EMAIL_CODE_TTL = 300  # 邮箱验证码 5 分钟


def generate_arithmetic():
    a = random.randint(1, 9)
    b = random.randint(1, 9)
    op = random.choice(["+", "-", "*"])
    answer = {"+": a + b, "-": a - b, "*": a * b}[op]
    cid = uuid.uuid4().hex
    _arith[cid] = {"answer": answer, "expire": time.time() + ARITH_TTL}
    return {"captcha_id": cid, "question": f"{a} {op} {b} = ?"}


def verify_arithmetic(captcha_id, answer):
    c = _arith.pop(captcha_id, None)  # 一次性，用后即删
    if not c or c["expire"] < time.time():
        return False
    try:
        return c["answer"] == int(answer)
    except (TypeError, ValueError):
        return False


def generate_email_code(email):
    code = f"{random.randint(100000, 999999)}"
    _codes[email] = {"code": code, "expire": time.time() + EMAIL_CODE_TTL}
    return code


def verify_email_code(email, code):
    c = _codes.get(email)
    if not c or c["expire"] < time.time():
        return False
    if c["code"] != str(code):
        return False
    _codes.pop(email)  # 一次性
    return True
