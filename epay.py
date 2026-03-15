#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
易支付对接模块
支持常见的易支付平台接口
"""

import hashlib
import urllib.parse
import requests
import json

# ============= 易支付配置 =============
# 请在这里填写你的易支付配置
EPAY_CONFIG = {
    'api_url': 'https://pay.example.com',  # 易支付 API 地址
    'pid': '10000',  # 商户 PID
    'key': 'your_secret_key',  # 商户密钥
}

def get_epay_config():
    """获取易支付配置（从环境变量或配置文件读取）"""
    import os
    return {
        'api_url': os.environ.get('EPAY_API_URL', EPAY_CONFIG['api_url']),
        'pid': os.environ.get('EPAY_PID', EPAY_CONFIG['pid']),
        'key': os.environ.get('EPAY_KEY', EPAY_CONFIG['key']),
    }

# ============= 签名验证 =============

def generate_sign(params, key):
    """生成易支付签名"""
    # 按参数名排序
    sorted_params = sorted(params.items())
    # 拼接参数字符串
    sign_str = '&'.join(f"{k}={v}" for k, v in sorted_params if v and k != 'sign')
    # 添加密钥
    sign_str += f"&key={key}"
    # MD5 签名
    return hashlib.md5(sign_str.encode('utf-8')).hexdigest()

def verify_sign(params, key):
    """验证易支付回调签名"""
    received_sign = params.get('sign', '')
    # 移除签名参数
    params_copy = {k: v for k, v in params.items() if k != 'sign' and k != 'sign_type'}
    # 生成签名
    expected_sign = generate_sign(params_copy, key)
    return received_sign == expected_sign

# ============= API 接口 =============

def create_order(order_no, amount, name, notify_url, return_url, client_ip='127.0.0.1'):
    """
    创建支付订单

    参数:
        order_no: 商户订单号
        amount: 订单金额（元）
        name: 商品名称
        notify_url: 异步通知地址
        return_url: 跳转返回地址
        client_ip: 客户端 IP

    返回:
        dict: {'code': 1, 'order_no': '...', 'qr_code': '...'}
    """
    config = get_epay_config()

    params = {
        'pid': config['pid'],
        'type': 'alipay',  # alipay 或 wxpay
        'out_trade_no': order_no,
        'notify_url': notify_url,
        'return_url': return_url,
        'name': name,
        'money': str(amount),
        'clientip': client_ip,
    }

    # 生成签名
    params['sign'] = generate_sign(params, config['key'])
    params['sign_type'] = 'MD5'

    # 调用易支付 API
    api_url = f"{config['api_url']}/mapi.php"
    try:
        resp = requests.post(api_url, data=params, timeout=10)
        result = resp.json()

        if result.get('code') == 1:
            return {
                'success': True,
                'order_no': order_no,
                'qr_code': result.get('qr_code'),  # 二维码链接
                'pay_url': result.get('payurl'),  # 支付跳转链接
            }
        else:
            return {
                'success': False,
                'error': result.get('msg', '创建订单失败'),
            }
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
        }

def check_order_status(order_no):
    """
    查询订单状态

    返回:
        dict: {'code': 1, 'status': 1}  # status: 0-待支付，1-已支付
    """
    config = get_epay_config()

    params = {
        'pid': config['pid'],
        'key': config['key'],
        'out_trade_no': order_no,
    }

    api_url = f"{config['api_url']}/mapi.php?act=order"
    try:
        resp = requests.post(api_url, data=params, timeout=10)
        result = resp.json()

        if result.get('code') == 1:
            return {
                'success': True,
                'status': result.get('status'),  # 0-待支付，1-已支付
                'trade_no': result.get('trade_no'),
            }
        else:
            return {
                'success': False,
                'error': result.get('msg', '查询失败'),
            }
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
        }

# ============= 回调处理 =============

def process_notify(request_data):
    """
    处理易支付异步通知

    返回:
        tuple: (success: bool, order_info: dict)
    """
    config = get_epay_config()

    # 验证签名
    if not verify_sign(request_data, config['key']):
        return False, {'error': '签名验证失败'}

    # 检查订单状态
    if request_data.get('trade_status') != 'TRADE_SUCCESS':
        return False, {'error': '订单未支付成功'}

    # 返回订单信息
    order_info = {
        'order_no': request_data.get('out_trade_no'),
        'trade_no': request_data.get('trade_no'),
        'amount': float(request_data.get('money', 0)),
        'pid': request_data.get('pid'),
    }

    return True, order_info

# ============= 测试 =============

if __name__ == '__main__':
    # 测试签名
    test_params = {
        'pid': '10000',
        'out_trade_no': 'ORD123456',
        'money': '9.99',
        'name': '测试商品',
    }
    sign = generate_sign(test_params, 'test_key')
    print(f"测试签名：{sign}")

    # 验证签名
    test_params['sign'] = sign
    result = verify_sign(test_params, 'test_key')
    print(f"签名验证：{result}")
