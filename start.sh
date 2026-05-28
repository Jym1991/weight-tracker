#!/bin/bash
cd "$(dirname "$0")"

# Create virtual env if not exists
if [ ! -d "venv" ]; then
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
else
    source venv/bin/activate
fi

echo "================================="
echo "  减肥体重管理系统"
echo "  打开浏览器访问 http://localhost:8000"
echo "  按 Ctrl+C 停止"
echo "================================="

uvicorn main:app --host 0.0.0.0 --port 8000
