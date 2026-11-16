import sys
import os
import asyncio

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import uvicorn
from app.main import app

if __name__ == "__main__":
    print("Starting IEEE Assistant backend on 127.0.0.1:8000...", flush=True)
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info", access_log=True)
