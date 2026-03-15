# Coze 插件配置指南（支持用户传入 Cookie）

## 服务地址

**API Base URL**: `http://59.110.232.247:8080`

---

## API 参数说明

### 通用解析端点 `/parse`

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `url` | string | ✅ 是 | 视频链接地址 |
| `platform` | string | ❌ 否 | 平台类型（douyin/xiaohongshu/bilibili），不传则自动识别 |
| `cookies` | string | ❌ 否 | Cookie 字符串，格式：`name=value; name2=value2` |

### 指定平台端点 `/parse/{platform}`

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `platform` | string (路径) | ✅ 是 | 平台类型（douyin/xiaohongshu/bilibili） |
| `url` | string (Body) | ✅ 是 | 视频链接地址 |
| `cookies` | string (Body) | ❌ 否 | Cookie 字符串 |

---

## 请求示例

### 1. 不传 Cookie（使用服务器配置的 Cookie）

```bash
curl -X POST http://59.110.232.247:8080/parse \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.douyin.com/video/xxx"}'
```

### 2. 传入 Cookie（推荐使用）

```bash
curl -X POST http://59.110.232.247:8080/parse/douyin \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://www.douyin.com/video/xxx",
    "cookies": "sessionid=abc123; __ac_nonce=xyz789"
  }'
```

### 3. B 站视频（传入 Cookie）

```bash
curl -X POST http://59.110.232.247:8080/parse/bilibili \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://www.bilibili.com/video/BV1xxx",
    "cookies": "DedeUserID=123456; buvid3=abc; captcha_token=xyz"
  }'
```

---

## OpenAPI Schema（Coze 插件配置）

```yaml
openapi: 3.0.0
info:
  title: 视频下载服务
  description: |
    解析抖音、小红书、B 站视频链接，获取无水印下载 URL

    ## 使用说明
    1. 传入视频链接
    2. 可选：传入 Cookie 字符串（提高解析成功率）
    3. 返回无水印下载链接

    ## Cookie 获取方法
    - 抖音：浏览器访问 www.douyin.com，F12 复制 Cookie
    - 小红书：浏览器访问 www.xiaohongshu.com，F12 复制 Cookie
    - B 站：浏览器访问 www.bilibili.com，F12 复制 Cookie
  version: 1.0.0
servers:
  - url: http://59.110.232.247:8080
paths:
  /parse:
    post:
      operationId: parseVideo
      summary: 解析视频链接（自动识别平台）
      description: 自动识别视频平台并解析，返回无水印下载 URL
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required:
                - url
              properties:
                url:
                  type: string
                  description: 视频链接地址
                  example: "https://www.douyin.com/video/123456789"
                platform:
                  type: string
                  description: 平台类型（可选，不传则自动识别）
                  enum: [douyin, xiaohongshu, bilibili]
                  example: "douyin"
                cookies:
                  type: string
                  description: Cookie 字符串，格式：name=value; name2=value2
                  example: "sessionid=abc123; __ac_nonce=xyz789"
      responses:
        '200':
          description: 成功
          content:
            application/json:
              schema:
                type: object
                properties:
                  success:
                    type: boolean
                    description: 是否解析成功
                  platform:
                    type: string
                    description: 视频平台名称
                  data:
                    type: object
                    properties:
                      title:
                        type: string
                        description: 视频标题
                      uploader:
                        type: string
                        description: 作者名
                      download_url:
                        type: string
                        description: 无水印视频下载链接
                      thumbnail:
                        type: string
                        description: 视频封面图 URL
                      duration:
                        type: integer
                        description: 视频时长（秒）
                  error:
                    type: string
                    description: 错误信息（失败时返回）

  /parse/{platform}:
    post:
      operationId: parseVideoByPlatform
      summary: 解析视频链接（指定平台）
      description: 指定视频平台并解析，返回无水印下载 URL
      parameters:
        - name: platform
          in: path
          required: true
          schema:
            type: string
            enum: [douyin, xiaohongshu, bilibili]
          description: 视频平台
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required:
                - url
              properties:
                url:
                  type: string
                  description: 视频链接地址
                  example: "https://www.bilibili.com/video/BV1xxx"
                cookies:
                  type: string
                  description: Cookie 字符串，格式：name=value; name2=value2
                  example: "DedeUserID=123456; buvid3=abc"
      responses:
        '200':
          description: 成功
          content:
            application/json:
              schema:
                type: object
                properties:
                  success:
                    type: boolean
                  platform:
                    type: string
                  data:
                    type: object
```

---

## Coze Bot 对话示例

### 场景 1：用户传入 Cookie

**用户**: 帮我下载这个抖音视频 https://www.douyin.com/video/xxx

**Bot**: 请提供 Cookie 以提高解析成功率。
       获取方法：浏览器访问 douyin.com，按 F12，复制 Cookie 字符串

**用户**: sessionid=abc123; __ac_nonce=xyz789

**Bot**: 正在解析...
       ✅ 解析成功
       平台：抖音
       标题：视频标题
       作者：@作者名
       下载链接：https://xxx.com/video.mp4

---

## Python 调用示例

```python
import requests

SERVER = "http://59.110.232.247:8080"

def parse_video(url: str, platform: str = None, cookies: str = None) -> dict:
    """
    解析视频链接

    Args:
        url: 视频链接
        platform: 可选，平台类型
        cookies: 可选，Cookie 字符串

    Returns:
        解析结果
    """
    api_url = f"{SERVER}/parse"
    if platform:
        api_url = f"{SERVER}/parse/{platform}"

    data = {"url": url}
    if cookies:
        data["cookies"] = cookies

    resp = requests.post(api_url, json=data)
    return resp.json()

# 使用示例
result = parse_video(
    url="https://www.douyin.com/video/xxx",
    platform="douyin",
    cookies="sessionid=abc123; __ac_nonce=xyz789"
)

if result.get("success"):
    print(f"下载链接：{result['data']['download_url']}")
else:
    print(f"解析失败：{result.get('error')}")
```

---

## Cookie 获取指南

### 通用方法（所有平台）

1. 浏览器（Chrome/Edge）访问对应网站
   - 抖音：https://www.douyin.com
   - 小红书：https://www.xiaohongshu.com
   - B 站：https://www.bilibili.com

2. 登录账号（如果需要）

3. 按 **F12** 打开开发者工具

4. 切换到 **Network**（网络）标签

5. 刷新页面

6. 点击第一个请求（通常是网站域名）

7. 在右侧 **Headers** 中找到 **Cookie** 字段

8. 复制完整的 Cookie 字符串

### Cookie 格式示例

```
sessionid=abc123; __ac_nonce=xyz789; __ac_signature=_02B4Z6wo00f01xxx
```

---

## 注意事项

1. **Cookie 安全**：不要在公开场合泄露 Cookie
2. **Cookie 有效期**：通常 7-30 天，过期需要重新获取
3. **解析失败**：可能是 Cookie 过期或视频已被删除
4. **推荐**：建议在 Bot 中引导用户提供 Cookie

---

## 完整响应示例

### 成功响应
```json
{
  "success": true,
  "platform": "抖音",
  "data": {
    "title": "视频标题",
    "uploader": "@作者名",
    "duration": 30,
    "thumbnail": "https://xxx.com/cover.jpg",
    "download_url": "https://xxx.com/video.mp4"
  }
}
```

### 失败响应
```json
{
  "success": false,
  "error": "需要 Cookie 才能解析，请在请求中添加 cookies 参数"
}
```
