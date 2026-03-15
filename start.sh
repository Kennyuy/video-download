#!/bin/bash
# 视频下载服务 - 启动脚本

cd /root/video-downloader

# 检查是否已有进程运行
if pgrep -f "python3 app.py" > /dev/null; then
    echo "服务已在运行中，PID: $(pgrep -f 'python3 app.py')"
    echo "如需重启，先运行：./stop.sh"
    exit 0
fi

# 启动服务
echo "启动视频下载服务..."
nohup python3 app.py > /root/video-downloader/service.log 2>&1 &

# 等待服务启动
sleep 3

# 检查服务状态
if pgrep -f "python3 app.py" > /dev/null; then
    echo "✅ 服务启动成功!"
    echo "服务地址：http://0.0.0.0:8080"
    echo "日志文件：/root/video-downloader/service.log"
    echo ""
    echo "停止服务：./stop.sh"
    echo "查看日志：tail -f service.log"
else
    echo "❌ 服务启动失败，请检查日志"
fi
