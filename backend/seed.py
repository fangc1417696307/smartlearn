from sqlalchemy.orm import Session
import models
import config
from security import hash_password

PERMISSIONS = [
    ("profile.manage", "学习画像", "构建与管理个人学习画像"),
    ("resource.view", "查看资源", "浏览学习资源"),
    ("resource.generate", "生成资源", "生成个性化学习资源"),
    ("path.manage", "学习路径", "查看与管理学习路径"),
    ("quiz.answer", "练习答题", "作答练习题目"),
    ("qa.ask", "智能答疑", "向智能体提问"),
    ("assessment.view", "学习评估", "查看学习效果评估"),
    ("student.view", "查看学生", "查看学生画像与学习情况"),
    ("user.manage", "用户管理", "管理用户账号"),
    ("role.manage", "角色管理", "管理角色与权限"),
    ("stats.view", "数据看板", "查看系统数据看板与统计"),
]

ROLES = [
    ("student", "学生", "学习者，使用画像/路径/资源/答疑/评估", [
        "profile.manage", "resource.view", "path.manage", "quiz.answer", "qa.ask", "assessment.view",
    ]),
    # 老师是教学管理者，不参与学生学习流程，因此不配置学习类权限
    # （画像/路径/资源/答题/答疑/评估属于学生功能）
    ("teacher", "老师", "查看学生学习情况", [
        "student.view",
    ]),
    ("admin", "管理员", "系统最高权限，管理用户与角色", None),  # None 表示全部权限
]


def seed(db: Session):
    # 权限
    perm_map = {}
    for code, name, desc in PERMISSIONS:
        p = db.query(models.Permission).filter(models.Permission.code == code).first()
        if not p:
            p = models.Permission(code=code, name=name, description=desc)
            db.add(p)
        perm_map[code] = p
    db.commit()

    # 角色
    for code, name, desc, perm_codes in ROLES:
        role = db.query(models.Role).filter(models.Role.code == code).first()
        if not role:
            role = models.Role(name=name, code=code, description=desc, is_system=True)
            db.add(role)
            db.flush()
        if perm_codes is None:
            role.permissions = list(perm_map.values())
        else:
            role.permissions = [perm_map[c] for c in perm_codes]
    db.commit()

    # 默认管理员
    admin = db.query(models.User).filter(models.User.account == "admin").first()
    if not admin:
        admin = models.User(
            account="admin", email="admin@smartlearn.edu",
            password_hash=hash_password(config.ADMIN_INITIAL_PASSWORD),
            nickname="系统管理员", major="",
            must_change_password=True,
        )
        admin.roles.append(db.query(models.Role).filter(models.Role.code == "admin").first())
        db.add(admin)
        db.commit()

    # 演示老师账号
    teacher = db.query(models.User).filter(models.User.account == "teacher01").first()
    if not teacher:
        teacher = models.User(
            account="teacher01", email="teacher01@smartlearn.edu",
            password_hash=hash_password("teacher123"),
            nickname="演示老师", major="计算机科学与技术",
        )
        teacher.roles.append(db.query(models.Role).filter(models.Role.code == "teacher").first())
        db.add(teacher)
        db.commit()

    # 演示学生账号
    student = db.query(models.User).filter(models.User.account == "student01").first()
    if not student:
        student = models.User(
            account="student01", email="student01@smartlearn.edu",
            password_hash=hash_password("student123"),
            nickname="演示学生", major="计算机科学与技术",
        )
        student.roles.append(db.query(models.Role).filter(models.Role.code == "student").first())
        db.add(student)
        db.commit()
