# -*- coding: utf-8 -*-
"""开发启动脚本：python run.py（改代码后请手动重启，勿依赖 --reload）"""
import uvicorn

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="127.0.0.1", port=8001, reload=False)
