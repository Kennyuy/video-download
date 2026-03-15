#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库模型 - 用户、API Key、订单管理
"""

import sqlite3
import os
from datetime import datetime, timedelta

DATABASE_PATH = os.path.join(os.path.dirname(__file__), 'database.db')

def get_db():
    """获取数据库连接"""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """初始化数据库表"""
    conn = get_db()
    cursor = conn.cursor()

    # 用户表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email VARCHAR(255) UNIQUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # API Key 表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS api_keys (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            api_key VARCHAR(255) UNIQUE NOT NULL,
            total_calls INTEGER DEFAULT 0,
            used_calls INTEGER DEFAULT 0,
            enabled INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')

    # 订单表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_no VARCHAR(64) UNIQUE NOT NULL,
            user_id INTEGER,
            api_key_id INTEGER,
            amount REAL NOT NULL,
            calls INTEGER DEFAULT 0,
            status INTEGER DEFAULT 0,
            pay_channel VARCHAR(32),
            trade_no VARCHAR(128),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            paid_at TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (api_key_id) REFERENCES api_keys(id)
        )
    ''')

    # 调用日志表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS call_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            api_key VARCHAR(255),
            platform VARCHAR(32),
            url TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (api_key) REFERENCES api_keys(api_key)
        )
    ''')

    conn.commit()
    conn.close()
    print("数据库初始化完成")

# ============= 用户操作 =============

def create_user(email=None):
    """创建用户"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('INSERT INTO users (email) VALUES (?)', (email,))
    user_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return user_id

def get_user(user_id):
    """获取用户信息"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
    user = cursor.fetchone()
    conn.close()
    return user

# ============= API Key 操作 =============

def create_api_key(user_id=None, total_calls=0, expires_days=None):
    """创建 API Key"""
    import secrets
    api_key = 'sk-' + secrets.token_hex(16)

    conn = get_db()
    cursor = conn.cursor()

    if expires_days:
        expires_at = datetime.now() + timedelta(days=expires_days)
    else:
        expires_at = None

    cursor.execute('''
        INSERT INTO api_keys (user_id, api_key, total_calls, used_calls, enabled, expires_at)
        VALUES (?, ?, ?, ?, 1, ?)
    ''', (user_id, api_key, total_calls, 0, expires_at))

    key_id = cursor.lastrowid
    conn.commit()
    conn.close()

    return {'id': key_id, 'api_key': api_key}

def get_api_key(api_key):
    """获取 API Key 信息"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM api_keys WHERE api_key = ?', (api_key,))
    key = cursor.fetchone()
    conn.close()
    return key

def verify_api_key(api_key):
    """验证 API Key（检查是否有效并扣除次数）"""
    conn = get_db()
    cursor = conn.cursor()

    # 获取 API Key 信息
    cursor.execute('''
        SELECT * FROM api_keys
        WHERE api_key = ? AND enabled = 1
        AND (expires_at IS NULL OR expires_at > datetime('now'))
    ''', (api_key,))
    key = cursor.fetchone()

    if not key:
        conn.close()
        return False, "无效的 API Key"

    # 检查剩余次数
    remaining = key['total_calls'] - key['used_calls']
    if remaining <= 0:
        conn.close()
        return False, "API Key 次数已用尽"

    # 扣除次数
    cursor.execute('''
        UPDATE api_keys SET used_calls = used_calls + 1 WHERE id = ?
    ''', (key['id'],))
    conn.commit()
    conn.close()

    return True, remaining - 1  # 返回剩余次数

def get_api_key_usage(api_key):
    """获取 API Key 使用详情"""
    key = get_api_key(api_key)
    if not key:
        return None

    remaining = key['total_calls'] - key['used_calls']
    return {
        'total_calls': key['total_calls'],
        'used_calls': key['used_calls'],
        'remaining': remaining,
        'enabled': bool(key['enabled']),
        'created_at': key['created_at'],
        'expires_at': key['expires_at']
    }

def update_api_key_enabled(api_key, enabled):
    """启用/禁用 API Key"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE api_keys SET enabled = ? WHERE api_key = ?
    ''', (1 if enabled else 0, api_key))
    conn.commit()
    affected = cursor.rowcount
    conn.close()
    return affected > 0

def get_all_api_keys():
    """获取所有 API Key 列表"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT ak.*, u.email
        FROM api_keys ak
        LEFT JOIN users u ON ak.user_id = u.id
        ORDER BY ak.created_at DESC
    ''')
    keys = cursor.fetchall()
    conn.close()
    return keys

# ============= 订单操作 =============

def create_order(user_id, amount, calls, pay_channel='alipay'):
    """创建订单"""
    import time
    order_no = f"ORD{int(time.time())}{os.urandom(3).hex()}"

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO orders (order_no, user_id, amount, calls, status, pay_channel)
        VALUES (?, ?, ?, ?, 0, ?)
    ''', (order_no, user_id, amount, calls, pay_channel))

    conn.commit()
    conn.close()

    return {'order_no': order_no, 'amount': amount, 'calls': calls}

def get_order(order_no):
    """获取订单信息"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM orders WHERE order_no = ?', (order_no,))
    order = cursor.fetchone()
    conn.close()
    return order

def update_order_status(order_no, status, trade_no=None):
    """更新订单状态"""
    conn = get_db()
    cursor = conn.cursor()

    if status == 1:  # 支付成功
        cursor.execute('''
            UPDATE orders
            SET status = 1, paid_at = datetime('now'), trade_no = ?
            WHERE order_no = ?
        ''', (trade_no, order_no))
    else:
        cursor.execute('''
            UPDATE orders SET status = ? WHERE order_no = ?
        ''', (status, order_no))

    conn.commit()
    affected = cursor.rowcount
    conn.close()
    return affected > 0

def get_user_orders(user_id):
    """获取用户订单列表"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM orders
        WHERE user_id = ?
        ORDER BY created_at DESC
    ''', (user_id,))
    orders = cursor.fetchall()
    conn.close()
    return orders

def get_all_orders():
    """获取所有订单"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT o.*, u.email, ak.api_key
        FROM orders o
        LEFT JOIN users u ON o.user_id = u.id
        LEFT JOIN api_keys ak ON o.api_key_id = ak.id
        ORDER BY o.created_at DESC
    ''')
    orders = cursor.fetchall()
    conn.close()
    return orders

# ============= 调用日志 =============

def log_api_call(api_key, platform, url):
    """记录 API 调用日志"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO call_logs (api_key, platform, url)
        VALUES (?, ?, ?)
    ''', (api_key, platform, url))
    conn.commit()
    conn.close()

def get_api_call_logs(api_key, limit=50):
    """获取 API Key 调用日志"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM call_logs
        WHERE api_key = ?
        ORDER BY created_at DESC
        LIMIT ?
    ''', (api_key, limit))
    logs = cursor.fetchall()
    conn.close()
    return logs

# 初始化数据库
if __name__ == '__main__':
    init_db()
