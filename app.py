#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
视频下载服务 - 支持抖音、小红书、B 站
通过 yt-dlp 解析视频链接，返回无水印下载 URL
支持用户传入 API Key 进行鉴权和计费
"""

from flask import Flask, request, jsonify
import yt_dlp
import os
import tempfile
import logging
import json

app = Flask(__name__)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 导入数据库模块
from database import verify_api_key, get_api_key_usage, log_api_call, get_all_api_keys, update_api_key_enabled, create_api_key

# 各平台的 yt-dlp 配置
PLATFORM_CONFIGS = {
    'douyin': {
        'name': '抖音',
        'domain': 'www.douyin.com',
        'extractors': ['douyin', 'tiktok'],
    },
    'xiaohongshu': {
        'name': '小红书',
        'domain': 'www.xiaohongshu.com',
        'extractors': ['xiaohongshu'],
    },
    'bilibili': {
        'name': 'B 站',
        'domain': 'www.bilibili.com',
        'extractors': ['bilibili', 'bilibili:channel'],
    }
}

def detect_platform(url):
    """根据 URL 自动检测视频平台"""
    if any(kw in url for kw in ['douyin.com', 'iesdouyin.com', 'tiktok.com']):
        return 'douyin'
    elif any(kw in url for kw in ['xiaohongshu.com', 'xhscdn.com']):
        return 'xiaohongshu'
    elif any(kw in url for kw in ['bilibili.com', 'b23.tv']):
        return 'bilibili'
    return None

def create_cookie_file(platform, cookie_string):
    """将 Cookie 字符串转换为 Netscape 格式并创建临时文件"""
    if not cookie_string:
        return None

    domain = PLATFORM_CONFIGS.get(platform, {}).get('domain', '')
    if not domain:
        return None

    temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt', encoding='utf-8')
    temp_file.write("# Netscape HTTP Cookie File\n")
    temp_file.write(f"# Generated for {platform}\n")

    # 清理 Cookie 字符串 - 处理可能的换行符和空格
    cookie_string = cookie_string.strip()
    # 替换可能的中文分号或全角字符
    cookie_string = cookie_string.replace('\n', ';').replace('\r', '')

    cookies = cookie_string.split(';')
    for cookie in cookies:
        cookie = cookie.strip()
        if not cookie or '=' not in cookie:
            continue

        parts = cookie.split('=', 1)
        if len(parts) != 2:
            continue

        name = parts[0].strip()
        value = parts[1].strip()

        # 验证 cookie 名称是否合法（只允许字母、数字、下划线、连字符）
        if not all(c.isalnum() or c in '_-' for c in name):
            continue

        if name and value:
            # Netscape 格式：domain flag path secure expiry name value
            line = domain + chr(9) + "TRUE" + chr(9) + "/" + chr(9) + "FALSE" + chr(9) + "9999999999" + chr(9) + name + chr(9) + value + "\n"
            temp_file.write(line)

    temp_file.close()
    return temp_file.name

def get_ydl_opts(platform, cookie_string=None):
    """获取 yt-dlp 配置"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }

    opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': False,
        'format': 'best',
        'noplaylist': True,
        'user_agent': headers['User-Agent'],
    }

    # 如果有 Cookie 字符串，直接添加到 headers 中
    if cookie_string:
        opts['http_headers'] = {
            'Cookie': cookie_string,
        }
        logger.info(f"使用 Cookie 字符串解析 {platform}")
    else:
        cookie_file = os.path.join(os.path.dirname(__file__), f'{platform}_cookies.txt')
        if os.path.exists(cookie_file):
            opts['cookiefile'] = cookie_file

    if platform == 'bilibili':
        opts['extractor_args'] = {
            'bilibili': {
                's_locale': 'zh_CN',
            }
        }

    return opts

def format_duration(seconds):
    """格式化时长"""
    if not seconds:
        return "0:00"
    minutes = int(seconds) // 60
    secs = int(seconds) % 60
    return f"{minutes}:{secs:02d}"

def format_size(bytes_val):
    """格式化文件大小"""
    if not bytes_val:
        return "未知"
    if bytes_val < 1024 * 1024:
        return f"{bytes_val / 1024:.1f}KB"
    elif bytes_val < 1024 * 1024 * 1024:
        return f"{bytes_val / (1024 * 1024):.1f}MB"
    else:
        return f"{bytes_val / (1024 * 1024 * 1024):.2f}GB"

def extract_video_info(url, platform, cookie_string=None):
    """提取视频信息"""
    try:
        opts = get_ydl_opts(platform, cookie_string)

        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)

            if not info:
                return None, "无法获取视频信息"

            if 'entries' in info and info['entries']:
                entries = list(info['entries'])
                if entries:
                    info = entries[0]

            # 构建下载链接列表
            download_urls = []

            # 直接 URL
            if info.get('url'):
                download_urls.append({
                    'quality': 'best',
                    'url': info['url'],
                    'size': format_size(info.get('filesize'))
                })

            # 多格式链接
            if info.get('formats') or info.get('requested_formats'):
                formats = info.get('requested_formats') or info.get('formats', [])
                added_qualities = set()

                for fmt in formats:
                    if not fmt.get('url'):
                        continue

                    # 获取画质信息
                    height = fmt.get('height', 0)
                    if height:
                        quality = f"{height}p"
                    else:
                        quality = fmt.get('format_note', 'unknown')

                    # 避免重复
                    if quality in added_qualities:
                        continue
                    added_qualities.add(quality)

                    download_urls.append({
                        'quality': quality,
                        'url': fmt['url'],
                        'size': format_size(fmt.get('filesize'))
                    })

            if not download_urls:
                return None, "无法获取下载链接"

            # 获取最佳画质的下载链接（第一个）
            best_url = download_urls[0].get('url', '')

            result = {
                'title': info.get('title', '未知标题'),
                'duration': format_duration(info.get('duration')),
                'download_url': best_url
            }

            return result, None

    except yt_dlp.utils.DownloadError as e:
        error_msg = str(e)
        if 'Fresh cookies' in error_msg or 'cookies needed' in error_msg.lower():
            return None, "需要 Cookie 才能解析，请在请求中添加 cookies 参数"
        return None, f"下载错误：{error_msg}"
    except Exception as e:
        return None, f"解析错误：{str(e)}"

def check_user_api_key(api_key):
    """检查用户传入的 API Key 是否有效（从数据库验证）"""
    if not api_key:
        return False, "缺少 api_key 参数"

    # 从数据库验证
    valid, result = verify_api_key(api_key)
    if not valid:
        return False, result

    remaining = result
    return True, remaining

@app.route('/health', methods=['GET'])
def health():
    """健康检查"""
    return jsonify({'code': 200, 'msg': '服务运行中', 'data': {}})

@app.route('/query', methods=['GET', 'POST'])
def query_api_key():
    """查询 API Key 使用情况"""
    # 支持 GET 和 POST 两种方式获取参数
    if request.method == 'POST':
        data = request.get_json() or request.form
    else:
        data = request.args

    api_key = data.get('api_key', '')
    if not api_key:
        return jsonify({'code': 400, 'msg': '缺少 api_key 参数', 'data': {}}), 400

    usage = get_api_key_usage(api_key)
    if not usage:
        return jsonify({'code': 404, 'msg': '无效的 API Key', 'data': {}}), 404

    return jsonify({'code': 200, 'msg': 'success', 'data': usage})

@app.route('/api/keys', methods=['GET', 'POST'])
def manage_api_keys():
    """管理 API Key（需要管理员权限）"""
    # 检查管理员权限（使用固定的管理员 Key）
    admin_key = os.environ.get('VIDEO_API_KEY', 'sk-admin-secret')
    request_key = request.headers.get('X-API-Key', '')

    if request_key != admin_key:
        return jsonify({'code': 403, 'msg': '需要管理员权限', 'data': {}}), 403

    if request.method == 'POST':
        data = request.get_json() or request.form
        action = data.get('action', 'create')

        if action == 'create':
            # 创建新的 API Key
            total_calls = int(data.get('calls', 0))
            expires_days = data.get('expires_days')
            if expires_days:
                expires_days = int(expires_days)

            result = create_api_key(user_id=None, total_calls=total_calls, expires_days=expires_days)
            return jsonify({'code': 200, 'msg': '创建成功', 'data': {'api_key': result['api_key']}})

        elif action == 'disable':
            key_to_disable = data.get('api_key')
            if key_to_disable:
                update_api_key_enabled(key_to_disable, False)
                return jsonify({'code': 200, 'msg': '已禁用', 'data': {}})

        elif action == 'enable':
            key_to_enable = data.get('api_key')
            if key_to_enable:
                update_api_key_enabled(key_to_enable, True)
                return jsonify({'code': 200, 'msg': '已启用', 'data': {}})

        elif action == 'list':
            keys = get_all_api_keys()
            keys_list = [
                {
                    'api_key': k['api_key'][:20] + '...',
                    'total_calls': k['total_calls'],
                    'used_calls': k['used_calls'],
                    'remaining': k['total_calls'] - k['used_calls'],
                    'enabled': bool(k['enabled']),
                    'email': k['email'],
                }
                for k in keys
            ]
            return jsonify({'code': 200, 'msg': 'success', 'data': {'keys': keys_list}})

    # GET 请求返回所有 Key 列表
    keys = get_all_api_keys()
    keys_list = [
        {
            'api_key': k['api_key'][:20] + '...',
            'total_calls': k['total_calls'],
            'used_calls': k['used_calls'],
            'remaining': k['total_calls'] - k['used_calls'],
            'enabled': bool(k['enabled']),
        }
        for k in keys
    ]
    return jsonify({'code': 200, 'msg': 'success', 'data': {'keys': keys_list}})

@app.route('/parse', methods=['GET', 'POST'])
def parse_video():
    """
    解析视频链接（支持 GET 和 POST）

    参数:
        url: 视频链接（必需）
        platform: 平台类型（可选）
        cookies: Cookie 字符串（可选）
        api_key: 用户 API Key（必需）
    """
    # 支持 GET 和 POST 两种方式获取参数
    if request.method == 'POST':
        data = request.get_json() or request.form
    else:
        data = request.args

    # 检查用户 API Key
    api_key = data.get('api_key', '')
    valid, error = check_user_api_key(api_key)
    if not valid:
        return jsonify({'code': 401, 'msg': error, 'data': {}}), 401

    if not data or 'url' not in data:
        return jsonify({'code': 400, 'msg': '缺少 url 参数', 'data': {}}), 400

    url = data.get('url', '').strip()
    platform = data.get('platform', '').lower()
    cookie_string = data.get('cookies', '')

    if not platform:
        platform = detect_platform(url)
        if not platform:
            return jsonify({'code': 400, 'msg': '无法识别平台，请指定 platform 参数', 'data': {}}), 400

    if platform not in PLATFORM_CONFIGS:
        return jsonify({'code': 400, 'msg': f'不支持的平台：{platform}', 'data': {}}), 400

    video_info, error = extract_video_info(url, platform, cookie_string)

    if error:
        return jsonify({'code': 500, 'msg': error, 'data': {}}), 500

    # 记录调用日志
    log_api_call(api_key, platform, url)

    return jsonify({'code': 200, 'msg': 'success', 'data': video_info})

@app.route('/parse/<platform>', methods=['POST', 'GET'])
def parse_video_by_platform(platform):
    """按平台解析视频链接"""
    if platform not in PLATFORM_CONFIGS:
        return jsonify({'code': 400, 'msg': f'不支持的平台：{platform}', 'data': {}}), 400

    # 支持 GET 和 POST 两种方式获取参数
    if request.method == 'POST':
        data = request.get_json() or request.form
    else:
        data = request.args

    # 检查用户 API Key
    api_key = data.get('api_key', '')
    valid, error = check_user_api_key(api_key)
    if not valid:
        return jsonify({'code': 401, 'msg': error, 'data': {}}), 401

    if not data or 'url' not in data:
        return jsonify({'code': 400, 'msg': '缺少 url 参数', 'data': {}}), 400

    url = data['url'].strip()
    cookie_string = data.get('cookies', '')

    video_info, error = extract_video_info(url, platform, cookie_string)

    if error:
        return jsonify({'code': 500, 'msg': error, 'data': {}}), 500

    # 记录调用日志
    log_api_call(api_key, platform, url)

    return jsonify({'code': 200, 'msg': 'success', 'data': video_info})

if __name__ == '__main__':
    # 初始化数据库
    from database import init_db
    init_db()

    print("启动视频下载服务...")
    print("支持的平台：抖音、小红书、B 站")
    print("服务地址：http://0.0.0.0:8080")
    print("\nAPI 端点:")
    print("  GET  /health          - 健康检查")
    print("  GET  /query           - 查询 API Key 使用情况")
    print("  GET/POST /api/keys    - 管理 API Key（需要管理员权限）")
    print("  GET/POST /parse       - 自动识别平台解析")
    print("  GET/POST /parse/<platform> - 指定平台解析")
    print("\n请求参数:")
    print("  url: 视频链接（必需）")
    print("  api_key: 用户 API Key（必需）")
    print("  platform: 平台类型（可选）")
    print("  cookies: Cookie 字符串（可选）")
    app.run(host='0.0.0.0', port=8080, debug=False)
