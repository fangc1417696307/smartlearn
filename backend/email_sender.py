import smtplib
from email.mime.text import MIMEText
from email.header import Header

import config


def send_email_code(to_email: str, code: str) -> bool:
    """发送验证码邮件。未配置授权码时降级为打印到控制台（开发用）。"""
    if not config.SMTP_AUTH_CODE:
        print(f"[SMTP 降级] 未配置授权码，验证码已打印：{to_email} -> {code}")
        return True

    msg = MIMEText(f"【SmartLearn】您的登录验证码是 {code}，5 分钟内有效。如非本人操作请忽略。", "plain", "utf-8")
    msg["From"] = config.SMTP_USER
    msg["To"] = to_email
    msg["Subject"] = Header("SmartLearn 登录验证码", "utf-8")
    try:
        server = smtplib.SMTP_SSL(config.SMTP_HOST, config.SMTP_PORT, timeout=10)
        server.login(config.SMTP_USER, config.SMTP_AUTH_CODE)
        server.sendmail(config.SMTP_USER, [to_email], msg.as_string())
        server.quit()
        return True
    except Exception as e:
        print(f"[SMTP 发送失败] {e}")
        return False
