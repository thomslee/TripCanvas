# -*- coding: utf-8 -*-
import paramiko
cli = paramiko.SSHClient()
cli.set_missing_host_key_policy(paramiko.AutoAddPolicy())
cli.connect('82.156.177.145', username='ubuntu', password='Thomslee0529', timeout=20)

# 在后端容器中创建 admin 用户
cmd = """docker exec trip-backend python -c "
from app.database import SessionLocal
from app.services.auth_service import hash_password
from app.models.user import User
db = SessionLocal()
u = db.query(User).filter(User.username=='admin').first()
if not u:
    u = User(username='admin', password_hash=hash_password('admin123'), role='admin', nickname='管理员')
    db.add(u)
    db.commit()
    print('admin 创建成功')
else:
    print('admin 已存在')
db.close()
" 2>&1"""
_, o, e = cli.exec_command(cmd)
print(o.read().decode())
print(e.read().decode())

# 测试登录
cmd2 = """curl -s -X POST http://127.0.0.1:8002/api/auth/login -H 'Content-Type: application/json' -d '{"username":"admin","password":"admin123"}'"""
_, o, _ = cli.exec_command(cmd2)
print("登录:", o.read().decode()[:200])

cli.close()
