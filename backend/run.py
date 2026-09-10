# -*- coding: utf-8 -*-
"""启动脚本：python run.py（开发用 127.0.0.1:8001，生产用环境变量覆盖）"""
import os
import uvicorn

if __name__ == "__main__":
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "8001"))
    uvicorn.run("app.main:app", host=host, port=port, reload=False)
