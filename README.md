# 视频下载服务平台

一个基于 Python Flask 的视频下载服务平台，支持抖音、小红书、B 站等主流短视频平台的视频解析与下载。提供完整的 API 接口、用户管理系统、支付系统集成和管理后台。

## 功能特点

- **多平台支持**：自动识别并解析抖音、小红书、B 站等平台的视频链接
- **API 鉴权与计费**：基于 API Key 的访问控制，支持按调用次数计费
- **在线支付**：集成易支付系统，支持支付宝和微信支付
- **用户管理**：完整的用户注册、API Key 管理、余额查询功能
- **管理后台**：可视化管理界面，支持 API Key 创建/禁用、订单管理、数据统计
- **套餐系统**：预置多种调用次数套餐，灵活选择

## 项目结构

```
video-platform/
├── app.py              # 主应用 - 视频解析 API 服务
├── web.py              # Web 网站 - 用户界面和支付功能
├── database.py         # 数据库操作模块
├── epay.py             # 易支付对接模块
├── requirements.txt    # Python 依赖
├── start.sh            # 服务启动脚本
├── stop.sh             # 服务停止脚本
├── video-downloader.service  # systemd 服务配置
├── API_DOC.md          # API 接口文档
├── COOKIE 配置指南.md   # Cookie 配置说明
└── Coze 配置指南.md     # Coze 插件配置说明
```

## 技术栈

- **后端框架**: Flask 2.0+
- **视频解析**: yt-dlp
- **数据库**: SQLite
- **支付接口**: 易支付

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置

根据需求修改以下配置：

- `epay.py`: 配置易支付参数（PID、密钥、API 地址）
- `app.py`: 配置管理员 API Key（环境变量 `VIDEO_API_KEY` 或默认值）

### 3. 启动服务

```bash
# 启动 API 服务（8080 端口）
python3 app.py

# 启动 Web 服务（5000 端口）
python3 web.py

# 或使用启动脚本
./start.sh
```

### 4. 使用 systemd 管理（可选）

```bash
# 复制服务配置
sudo cp video-downloader.service /etc/systemd/system/

# 启动服务
sudo systemctl daemon-reload
sudo systemctl start video-downloader
sudo systemctl enable video-downloader
```

## API 接口

### 视频解析

| 端点 | 方法 | 说明 |
|------|------|------|
| `/parse` | GET/POST | 自动识别平台解析 |
| `/parse/<platform>` | GET/POST | 指定平台解析（douyin/xiaohongshu/bilibili） |
| `/health` | GET | 健康检查 |
| `/query` | GET/POST | 查询 API Key 使用情况 |
| `/api/keys` | GET/POST | 管理 API Key（需管理员权限） |

### 请求参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `url` | string | 是 | 视频链接 |
| `api_key` | string | 是 | 用户 API Key |
| `platform` | string | 否 | 平台类型（douyin/xiaohongshu/bilibili） |
| `cookies` | string | 否 | Cookie 字符串（用于需要登录的平台） |

### 请求示例

```bash
# 自动识别平台
curl -X POST "http://localhost:8080/parse" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://v.douyin.com/xxx", "api_key": "sk-xxx"}'

# 指定平台
curl -X POST "http://localhost:8080/parse/douyin" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://v.douyin.com/xxx", "api_key": "sk-xxx"}'
```

### 响应示例

```json
{
  "code": 200,
  "msg": "success",
  "data": {
    "title": "视频标题",
    "duration": "1:30",
    "download_url": "https://..."
  }
}
```

## 套餐价格

| 套餐 | 调用次数 | 价格 | 单价 |
|------|----------|------|------|
| 体验包 | 100 | ¥1.99 | ¥0.02/次 |
| 标准包 | 500 | ¥9.99 | ¥0.02/次 |
| 进阶包 | 1000 | ¥19.99 | ¥0.02/次 |
| 专业包 | 5000 | ¥49.99 | ¥0.01/次 |
| 企业包 | 10000 | ¥99.99 | ¥0.01/次 |

## 管理后台

访问 `/admin` 进入管理后台，默认管理员 API Key 为：

- 环境变量 `VIDEO_API_KEY`（优先）
- 默认值：`sk-admin-secret`

管理功能：
- 创建/禁用/启用 API Key
- 查看所有 API Key 列表及使用统计
- 查看订单列表和收入统计

## 环境变量

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `VIDEO_API_KEY` | 管理员 API Key | `sk-admin-secret` |
| `EPAY_API_URL` | 易支付 API 地址 | - |
| `EPAY_PID` | 易支付商户 PID | - |
| `EPAY_KEY` | 易支付商户密钥 | - |

## 相关文档

- [API_DOC.md](./API_DOC.md) - 详细 API 接口文档
- [COOKIE 配置指南.md](./COOKIE 配置指南.md) - Cookie 配置说明
- [Coze 配置指南.md](./Coze 配置指南.md) - Coze 插件配置说明

## 注意事项

1. 部分平台（如抖音）可能需要 Cookie 才能获取高质量下载链接
2. 请遵守各平台的使用条款和版权规定
3. 建议在生产环境使用反向代理（如 Nginx）和 HTTPS

## License

MIT License
