#!/bin/bash
# 视频下载服务 - 停止脚本

cd /root/video-downloader

# 停止服务
if pgrep -f "python3 app.py" > /dev/null; then
    echo "停止服务..."
    pkill -f "python3 app.py"
    sleep 2
    echo "✅ 服务已停止"
else
    echo "服务未运行"
fi
