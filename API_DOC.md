# 视频下载服务 API 文档

## 服务端部署

你的云服务器已部署视频下载服务：
- **地址**: `http://你的服务器IP:8080`
- **支持平台**: 抖音、小红书、B 站

## API 端点

### 1. 健康检查
```
GET /health
```

**响应示例**:
```json
{"status": "ok", "message": "视频下载服务运行中"}
```

---

### 2. 自动识别平台解析
```
POST /parse
Content-Type: application/json

{
    "url": "https://视频链接"
}
```

**响应示例**:
```json
{
    "success": true,
    "platform": "抖音",
    "data": {
        "title": "视频标题",
        "uploader": "作者名",
        "duration": 30,
        "thumbnail": "https://封面图链接",
        "download_url": "https://无水印视频下载链接",
        "platform": "douyin"
    }
}
```

---

### 3. 指定平台解析
```
POST /parse/douyin
POST /parse/xiaohongshu
POST /parse/bilibili
Content-Type: application/json

{
    "url": "https://视频链接"
}
```

---

## Coze IDE 调用示例

### Python 代码

```python
import requests

# 你的服务器地址
SERVER_URL = "http://你的服务器 IP:8080"

def download_video(url: str, platform: str = None) -> dict:
    """
    下载视频

    Args:
        url: 视频链接
        platform: 可选，指定平台 (douyin/xiaohongshu/bilibili)

    Returns:
        包含下载链接的字典
    """
    api_url = f"{SERVER_URL}/parse"
    if platform:
        api_url = f"{SERVER_URL}/parse/{platform}"

    response = requests.post(api_url, json={"url": url})
    result = response.json()

    if result.get("success"):
        return {
            "download_url": result["data"]["download_url"],
            "title": result["data"]["title"],
            "platform": result["platform"]
        }
    else:
        return {"error": result.get("error")}

# 使用示例
if __name__ == "__main__":
    # 抖音视频
    douyin_url = "https://v.douyin.com/xxxx"
    result = download_video(douyin_url)
    print(f"下载链接：{result.get('download_url')}")
```

### Coze Bot 插件配置

在 Coze 中创建插件时，配置如下：

**API Schema**:
```yaml
openapi: 3.0.0
info:
  title: 视频下载服务
  version: 1.0.0
paths:
  /parse:
    post:
      operationId: parseVideo
      summary: 解析视频链接获取下载 URL
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
                  description: 视频链接
      responses:
        '200':
          description: 成功返回下载链接
```

---

## 错误处理

| 错误码 | 说明 |
|--------|------|
| 400 | 请求参数错误或平台不支持 |
| 500 | 视频解析失败（链接无效/视频已删除等） |

**错误响应示例**:
```json
{
    "success": false,
    "error": "无法识别视频平台，请指定 platform 参数"
}
```
