#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
视频下载服务 - Web 网站
提供用户界面和支付功能
"""

from flask import Flask, request, jsonify, render_template_string, redirect, url_for
import os
import time
from database import (
    init_db, create_api_key, get_api_key_usage, get_all_api_keys,
    create_order, get_order, update_order_status, get_all_orders,
    update_api_key_enabled
)
from epay import create_order as epay_create_order, process_notify

app = Flask(__name__)

# 配置
PRICE_PER_CALL = 0.01  # 每次调用价格（元）

# ============= 套餐配置 =============
PACKAGES = [
    {'calls': 100, 'price': 1.99, 'name': '体验包'},
    {'calls': 500, 'price': 9.99, 'name': '标准包'},
    {'calls': 1000, 'price': 19.99, 'name': '进阶包'},
    {'calls': 5000, 'price': 49.99, 'name': '专业包'},
    {'calls': 10000, 'price': 99.99, 'name': '企业包'},
]

# ============= 页面模板 =============

BASE_TEMPLATE = '''
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title }} - 视频下载服务</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; line-height: 1.6; color: #333; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; padding: 20px; }
        .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 40px 20px; text-align: center; }
        .header h1 { font-size: 2.5rem; margin-bottom: 10px; }
        .header p { opacity: 0.9; font-size: 1.1rem; }
        .nav { background: white; box-shadow: 0 2px 4px rgba(0,0,0,0.1); padding: 15px 20px; }
        .nav ul { list-style: none; display: flex; gap: 30px; justify-content: center; }
        .nav a { color: #667eea; text-decoration: none; font-weight: 500; }
        .nav a:hover { text-decoration: underline; }
        .content { padding: 40px 20px; }
        .card { background: white; border-radius: 10px; padding: 30px; margin-bottom: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }
        .card h2 { color: #667eea; margin-bottom: 20px; }
        .btn { display: inline-block; padding: 12px 30px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; text-decoration: none; border-radius: 25px; font-weight: 500; border: none; cursor: pointer; }
        .btn:hover { opacity: 0.9; }
        .btn-outline { background: transparent; border: 2px solid #667eea; color: #667eea; }
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; }
        .package-card { background: white; border-radius: 10px; padding: 25px; text-align: center; border: 2px solid transparent; transition: all 0.3s; }
        .package-card:hover { transform: translateY(-5px); box-shadow: 0 10px 30px rgba(0,0,0,0.15); }
        .package-card.featured { border-color: #667eea; }
        .package-card .name { font-size: 1.3rem; color: #667eea; margin-bottom: 10px; }
        .package-card .calls { font-size: 2.5rem; font-weight: bold; color: #333; }
        .package-card .price { font-size: 1.5rem; color: #e74c3c; margin: 15px 0; }
        .package-card .desc { color: #666; font-size: 0.9rem; }
        .form-group { margin-bottom: 20px; }
        .form-group label { display: block; margin-bottom: 8px; font-weight: 500; }
        .form-group input, .form-group select { width: 100%; padding: 12px; border: 1px solid #ddd; border-radius: 8px; font-size: 1rem; }
        .form-group input:focus { outline: none; border-color: #667eea; }
        .alert { padding: 15px 20px; border-radius: 8px; margin-bottom: 20px; }
        .alert-success { background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
        .alert-error { background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
        .alert-info { background: #d1ecf1; color: #0c5460; border: 1px solid #bee5eb; }
        .qr-code { text-align: center; padding: 20px; }
        .qr-code img { max-width: 300px; }
        .stat-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; }
        .stat-card { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 25px; border-radius: 10px; text-align: center; }
        .stat-card .value { font-size: 2.5rem; font-weight: bold; }
        .stat-card .label { opacity: 0.9; margin-top: 5px; }
        table { width: 100%; border-collapse: collapse; margin-top: 20px; }
        th, td { padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }
        th { background: #f8f9fa; font-weight: 600; }
        .badge { display: inline-block; padding: 4px 12px; border-radius: 20px; font-size: 0.85rem; }
        .badge-success { background: #d4edda; color: #155724; }
        .badge-warning { background: #fff3cd; color: #856404; }
        .badge-danger { background: #f8d7da; color: #721c24; }
        .footer { text-align: center; padding: 30px; color: #666; }
        @media (max-width: 768px) { .header h1 { font-size: 1.8rem; } .grid { grid-template-columns: 1fr; } }
    </style>
</head>
<body>
    <div class="header">
        <h1>🎬 视频下载服务</h1>
        <p>支持抖音、小红书、B 站视频解析下载</p>
    </div>
    <div class="nav">
        <ul>
            <li><a href="/">首页</a></li>
            <li><a href="/packages">套餐价格</a></li>
            <li><a href="/query">查询余额</a></li>
            <li><a href="/admin">管理后台</a></li>
        </ul>
    </div>
    <div class="content">
        {{ content|safe }}
    </div>
    <div class="footer">
        <p>&copy; 2024 视频下载服务。All rights reserved.</p>
    </div>
</body>
</html>
'''

HOME_TEMPLATE = '''
<div class="card">
    <h2>欢迎使用视频下载服务</h2>
    <p style="font-size: 1.1rem; color: #666; margin-bottom: 30px;">
        本服务支持抖音、小红书、B 站等平台的视频解析下载，提供稳定的 API 接口，
        可按需购买调用次数，广泛应用于数据分析、内容归档等场景。
    </p>
    <div class="grid">
        <div class="card" style="text-align: center;">
            <h3 style="color: #667eea; margin-bottom: 10px;">🚀 快速接入</h3>
            <p style="color: #666;">简单的 API 接口，几行代码即可接入</p>
        </div>
        <div class="card" style="text-align: center;">
            <h3 style="color: #667eea; margin-bottom: 10px;">💰 按需付费</h3>
            <p style="color: #666;">0.01 元/次，用多少买多少</p>
        </div>
        <div class="card" style="text-align: center;">
            <h3 style="color: #667eea; margin-bottom: 10px;">🔒 稳定可靠</h3>
            <p style="color: #666;">7x24 小时服务，SLA 保障</p>
        </div>
    </div>
    <div style="text-align: center; margin-top: 30px;">
        <a href="/packages" class="btn">查看套餐</a>
        <a href="/query" class="btn btn-outline" style="margin-left: 10px;">查询余额</a>
    </div>
</div>
<div class="card">
    <h2>API 使用示例</h2>
    <pre style="background: #f8f9fa; padding: 20px; border-radius: 8px; overflow-x: auto;">
<code style="color: #333;">import requests

# 解析视频
response = requests.post(
    'https://download.kenny.help/parse',
    json={
        'url': 'https://www.douyin.com/video/xxx',
        'api_key': 'your_api_key'
    }
)

result = response.json()
print(result['data']['download_url'])</code></pre>
</div>
'''

PACKAGES_TEMPLATE = '''
<div class="card">
    <h2>套餐价格</h2>
    <p style="color: #666; margin-bottom: 30px;">
        单价：<strong>0.01 元/次</strong>，购买套餐更优惠
    </p>
    <div class="grid">
        {% for pkg in packages %}
        <div class="package-card {{ 'featured' if loop.index == 2 else '' }}">
            <div class="name">{{ pkg.name }}</div>
            <div class="calls">{{ pkg.calls }}</div>
            <div class="desc">次调用</div>
            <div class="price">¥{{ "%.2f"|format(pkg.price) }}</div>
            <div class="desc">约 ¥{{ "%.3f"|format(pkg.price / pkg.calls) }}/次</div>
            <form action="/buy" method="POST" style="margin-top: 20px;">
                <input type="hidden" name="calls" value="{{ pkg.calls }}">
                <input type="hidden" name="price" value="{{ pkg.price }}">
                <input type="hidden" name="name" value="{{ pkg.name }}">
                <button type="submit" class="btn">立即购买</button>
            </form>
        </div>
        {% endfor %}
    </div>
</div>
'''

BUY_TEMPLATE = '''
<div class="card" style="max-width: 600px; margin: 0 auto;">
    <h2>购买套餐</h2>
    <div class="alert alert-info">
        <strong>{{ package_name }}</strong><br>
        调用次数：{{ calls }} 次<br>
        订单金额：¥{{ "%.2f"|format(price) }}
    </div>

    {% if error %}
    <div class="alert alert-error">{{ error }}</div>
    {% endif %}

    <form method="POST">
        <div class="form-group">
            <label>已有 API Key？（可选）</label>
            <input type="text" name="existing_api_key" placeholder="输入已有的 API Key，留空则自动创建新的">
        </div>
        <div class="form-group">
            <label>支付方式</label>
            <select name="pay_channel" id="pay_channel" onchange="updatePayment()">
                <option value="alipay">支付宝</option>
                <option value="wxpay">微信支付</option>
            </select>
        </div>
        <button type="submit" class="btn" style="width: 100%;">生成支付订单</button>
    </form>
</div>

{% if qr_code %}
<div class="card" style="max-width: 600px; margin: 20px auto;">
    <h3 style="text-align: center; margin-bottom: 20px;">扫码支付</h3>
    <div class="qr-code">
        <img src="https://api.qrserver.com/v1/create-qr-code/?size=300x300&data={{ qr_code }}" alt="支付二维码">
    </div>
    <p style="text-align: center; color: #666; margin-top: 20px;">
        订单号：{{ order_no }}<br>
        金额：¥{{ "%.2f"|format(price) }}
    </p>
    <div style="text-align: center; margin-top: 20px;">
        <button class="btn btn-outline" onclick="checkStatus()">检查支付状态</button>
    </div>
</div>

<script>
function checkStatus() {
    fetch('/api/order_status?order_no={{ order_no }}')
        .then(r => r.json())
        .then(data => {
            if (data.paid) {
                alert('支付成功！');
                window.location.href = '/query?api_key={{ api_key }}';
            } else {
                alert('尚未支付，请扫码后刷新页面');
            }
        });
}
</script>
{% endif %}
'''

QUERY_TEMPLATE = '''
<div class="card" style="max-width: 600px; margin: 0 auto;">
    <h2>查询 API Key</h2>

    {% if error %}
    <div class="alert alert-error">{{ error }}</div>
    {% endif %}

    {% if usage %}
    <div class="stat-grid" style="margin-top: 20px;">
        <div class="stat-card">
            <div class="value">{{ usage.remaining }}</div>
            <div class="label">剩余次数</div>
        </div>
        <div class="stat-card" style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);">
            <div class="value">{{ usage.used_calls }}</div>
            <div class="label">已使用</div>
        </div>
        <div class="stat-card" style="background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);">
            <div class="value">{{ usage.total_calls }}</div>
            <div class="label">总次数</div>
        </div>
    </div>

    <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #eee;">
        <p><strong>API Key:</strong> <code style="background: #f8f9fa; padding: 5px 10px; border-radius: 4px;">{{ api_key }}</code></p>
        <p style="color: #666; margin-top: 10px;">
            <strong>状态：</strong>{{ '✅ 已启用' if usage.enabled else '❌ 已禁用' }}<br>
            {% if usage.expires_at %}
            <strong>过期时间：</strong>{{ usage.expires_at }}
            {% else %}
            <strong>有效期：</strong>永久有效
            {% endif %}
        </p>
    </div>
    {% else %}
    <form method="POST" style="margin-top: 20px;">
        <div class="form-group">
            <label>API Key</label>
            <input type="text" name="api_key" placeholder="输入 API Key" value="{{ api_key_input or '' }}">
        </div>
        <button type="submit" class="btn" style="width: 100%;">查询</button>
    </form>
    {% endif %}
</div>
'''

ADMIN_TEMPLATE = '''
<div class="card">
    <h2>管理后台</h2>

    {% if not is_admin %}
    <div class="alert alert-error">需要管理员权限</div>
    <form method="POST" style="max-width: 400px;">
        <div class="form-group">
            <label>管理员 API Key</label>
            <input type="text" name="admin_key" placeholder="输入管理员 API Key">
        </div>
        <button type="submit" class="btn">验证</button>
    </form>
    {% else %}

    <div class="stat-grid" style="margin-bottom: 30px;">
        <div class="stat-card">
            <div class="value">{{ stats.total_keys }}</div>
            <div class="label">API Key 总数</div>
        </div>
        <div class="stat-card" style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);">
            <div class="value">{{ stats.total_orders }}</div>
            <div class="label">总订单数</div>
        </div>
        <div class="stat-card" style="background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);">
            <div class="value">¥{{ "%.2f"|format(stats.total_revenue) }}</div>
            <div class="label">总收入</div>
        </div>
    </div>

    <h3>创建 API Key</h3>
    <form method="POST" action="/admin/create_key" style="max-width: 600px; margin-top: 20px;">
        <div class="form-group">
            <label>调用次数</label>
            <input type="number" name="calls" placeholder="0 表示无限次" value="1000">
        </div>
        <div class="form-group">
            <label>有效期（天，留空表示永久）</label>
            <input type="number" name="expires_days" placeholder="30">
        </div>
        <button type="submit" class="btn">创建</button>
    </form>

    <h3 style="margin-top: 40px;">API Key 列表</h3>
    <table>
        <thead>
            <tr>
                <th>API Key</th>
                <th>总次数</th>
                <th>已使用</th>
                <th>剩余</th>
                <th>状态</th>
                <th>操作</th>
            </tr>
        </thead>
        <tbody>
            {% for key in keys %}
            <tr>
                <td><code>{{ key.api_key }}</code></td>
                <td>{{ key.total_calls }}</td>
                <td>{{ key.used_calls }}</td>
                <td>{{ key.total_calls - key.used_calls }}</td>
                <td>
                    {% if key.enabled %}
                    <span class="badge badge-success">正常</span>
                    {% else %}
                    <span class="badge badge-danger">禁用</span>
                    {% endif %}
                </td>
                <td>
                    {% if key.enabled %}
                    <form method="POST" action="/admin/disable_key" style="display:inline;">
                        <input type="hidden" name="api_key" value="{{ key.api_key }}">
                        <button type="submit" class="btn btn-outline" style="padding: 4px 12px; font-size: 0.85rem;">禁用</button>
                    </form>
                    {% else %}
                    <form method="POST" action="/admin/enable_key" style="display:inline;">
                        <input type="hidden" name="api_key" value="{{ key.api_key }}">
                        <button type="submit" class="btn btn-outline" style="padding: 4px 12px; font-size: 0.85rem;">启用</button>
                    </form>
                    {% endif %}
                </td>
            </tr>
            {% endfor %}
        </tbody>
    </table>

    <h3 style="margin-top: 40px;">订单列表</h3>
    <table>
        <thead>
            <tr>
                <th>订单号</th>
                <th>金额</th>
                <th>次数</th>
                <th>状态</th>
                <th>时间</th>
            </tr>
        </thead>
        <tbody>
            {% for order in orders %}
            <tr>
                <td><code>{{ order.order_no }}</code></td>
                <td>¥{{ "%.2f"|format(order.amount) }}</td>
                <td>{{ order.calls }}</td>
                <td>
                    {% if order.status == 1 %}
                    <span class="badge badge-success">已支付</span>
                    {% else %}
                    <span class="badge badge-warning">待支付</span>
                    {% endif %}
                </td>
                <td>{{ order.created_at }}</td>
            </tr>
            {% endfor %}
        </tbody>
    </table>

    {% endif %}
</div>
'''

# ============= 路由 =============

@app.route('/')
def index():
    return render_template_string(BASE_TEMPLATE, title='首页', content=HOME_TEMPLATE)

@app.route('/packages')
def packages():
    return render_template_string(BASE_TEMPLATE, title='套餐价格',
        content=PACKAGES_TEMPLATE, packages=PACKAGES)

@app.route('/buy', methods=['GET', 'POST'])
def buy():
    if request.method == 'GET':
        calls = int(request.args.get('calls', 100))
        price = float(request.args.get('price', 1.99))
        name = request.args.get('name', '体验包')
        return render_template_string(BASE_TEMPLATE, title='购买',
            content=BUY_TEMPLATE, package_name=name, calls=calls, price=price,
            error=None, qr_code=None, order_no=None, api_key=None)

    # POST: 生成订单
    calls = int(request.form.get('calls', 100))
    price = float(request.form.get('price', 1.99))
    name = request.form.get('name', '体验包')
    existing_key = request.form.get('existing_api_key', '')
    pay_channel = request.form.get('pay_channel', 'alipay')

    # 创建订单（先不创建 API Key，等支付成功后再创建）
    order = create_order(user_id=None, amount=price, calls=calls)

    # 调用易支付创建订单
    notify_url = request.url_root.rstrip('/') + '/notify'
    return_url = request.url_root.rstrip('/') + '/query'

    result = epay_create_order(
        order_no=order['order_no'],
        amount=price,
        name=f'视频下载 API - {name}',
        notify_url=notify_url,
        return_url=return_url,
    )

    if not result['success']:
        return render_template_string(BASE_TEMPLATE, title='购买',
            content=BUY_TEMPLATE, package_name=name, calls=calls, price=price,
            error=result.get('error', '创建订单失败'), qr_code=None, order_no=None, api_key=None)

    # 将订单信息存入 session（简化用 query 参数传递）
    return render_template_string(BASE_TEMPLATE, title='购买',
        content=BUY_TEMPLATE, package_name=name, calls=calls, price=price,
        error=None, qr_code=result.get('qr_code', ''), order_no=order['order_no'], api_key='')

@app.route('/notify', methods=['POST'])
def notify():
    """易支付异步通知"""
    data = request.form.to_dict()

    success, order_info = process_notify(data)

    if success:
        # 验证订单金额
        order = get_order(order_info['order_no'])
        if order and order['amount'] == order_info['amount']:
            # 创建 API Key
            api_key_info = create_api_key(user_id=None, total_calls=order['calls'])

            # 更新订单状态
            update_order_status(order_info['order_no'], status=1, trade_no=order_info.get('trade_no'))

            # 将 API Key 存入订单
            from database import get_db
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute('UPDATE orders SET api_key_id = ? WHERE order_no = ?',
                          (api_key_info['id'], order_info['order_no']))
            conn.commit()
            conn.close()

    return 'success'

@app.route('/query', methods=['GET', 'POST'])
def query():
    if request.method == 'GET':
        api_key = request.args.get('api_key', '')
        return render_template_string(BASE_TEMPLATE, title='查询',
            content=QUERY_TEMPLATE, api_key_input=api_key, usage=None, error=None)

    # POST: 查询
    api_key = request.form.get('api_key', '')

    from database import get_api_key_usage
    usage = get_api_key_usage(api_key)

    if not usage:
        return render_template_string(BASE_TEMPLATE, title='查询',
            content=QUERY_TEMPLATE, api_key_input=api_key, usage=None,
            error='无效的 API Key')

    return render_template_string(BASE_TEMPLATE, title='查询',
        content=QUERY_TEMPLATE, api_key_input=api_key, usage=usage, error=None, api_key=api_key)

@app.route('/api/order_status')
def order_status():
    """检查订单状态"""
    order_no = request.args.get('order_no', '')
    order = get_order(order_no)

    if not order:
        return jsonify({'paid': False, 'error': '订单不存在'})

    return jsonify({'paid': order['status'] == 1, 'status': order['status']})

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    is_admin = request.cookies.get('is_admin') == '1'

    if request.method == 'POST':
        admin_key = request.form.get('admin_key', '')
        # 验证管理员权限
        if admin_key == os.environ.get('VIDEO_API_KEY', 'sk-admin-secret'):
            resp = redirect('/admin')
            resp.set_cookie('is_admin', '1')
            return resp
        else:
            return render_template_string(BASE_TEMPLATE, title='管理后台',
                content=ADMIN_TEMPLATE, is_admin=False, stats={}, keys=[], orders=[])

    if not is_admin:
        return render_template_string(BASE_TEMPLATE, title='管理后台',
            content=ADMIN_TEMPLATE, is_admin=False, stats={}, keys=[], orders=[])

    # 获取统计数据
    keys = get_all_api_keys()
    orders = get_all_orders()

    stats = {
        'total_keys': len(keys),
        'total_orders': len([o for o in orders if o['status'] == 1]),
        'total_revenue': sum([o['amount'] for o in orders if o['status'] == 1]),
    }

    keys_data = [
        {
            'api_key': k['api_key'],
            'total_calls': k['total_calls'],
            'used_calls': k['used_calls'],
            'enabled': bool(k['enabled']),
        }
        for k in keys
    ]

    orders_data = [
        {
            'order_no': o['order_no'],
            'amount': o['amount'],
            'calls': o['calls'],
            'status': o['status'],
            'created_at': o['created_at'],
        }
        for o in orders
    ]

    return render_template_string(BASE_TEMPLATE, title='管理后台',
        content=ADMIN_TEMPLATE, is_admin=True, stats=stats, keys=keys_data, orders=orders_data)

@app.route('/admin/create_key', methods=['POST'])
def admin_create_key():
    admin_key = request.cookies.get('admin_key', '')
    if admin_key != os.environ.get('VIDEO_API_KEY', 'sk-admin-secret'):
        return redirect('/admin')

    calls = int(request.form.get('calls', 0))
    expires_days = request.form.get('expires_days')
    if expires_days:
        expires_days = int(expires_days)

    result = create_api_key(user_id=None, total_calls=calls, expires_days=expires_days)

    return redirect('/admin')

@app.route('/admin/disable_key', methods=['POST'])
def admin_disable_key():
    if request.cookies.get('is_admin') != '1':
        return redirect('/admin')

    api_key = request.form.get('api_key', '')
    update_api_key_enabled(api_key, False)
    return redirect('/admin')

@app.route('/admin/enable_key', methods=['POST'])
def admin_enable_key():
    if request.cookies.get('is_admin') != '1':
        return redirect('/admin')

    api_key = request.form.get('api_key', '')
    update_api_key_enabled(api_key, True)
    return redirect('/admin')

if __name__ == '__main__':
    init_db()
    print("启动 Web 服务...")
    print("服务地址：http://0.0.0.0:5000")
    app.run(host='0.0.0.0', port=5000, debug=False)
