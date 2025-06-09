# MQTT 服务器下载 M3U8 视频文件

## 先决条件
1. 安装 [uv](https://github.com/astral-sh/uv)。 
```bash
# On macOS and Linux.
curl -LsSf https://astral.sh/uv/install.sh | sh
```
2. 安装 [`m3u8-downloader`](https://github.com/forkdo/m3u8-downloader)。
```bash
curl -L https://s.fx4.cn/m3u8-downloader | bash
```

## 安装

1. 拉取代码并进入项目目录：
   ```bash
   git clone <repository-url>
   cd video-downloader
   ```
2. 安装依赖：
   ```bash
   uv sync
   ```
   
## 使用
1. 启动 MQTT 服务器
2. 启动本服务
```bash
uv sync
. .venv/bin/activate
uv run video-downloader
```
3. 使用客户端，发布消息（`JSON`）到主题 `video/download/request`，格式如下：   
建议 `QOS` 为 `0`, `retain` 为 `false`。若 `retain` 为 `true`，则消息会被保留，直到有新的消息发布到相同的主题。会导致重启服务器后，重复下载相同的文件。
```bash
{
  "url": "https://test.com/50941.m3u8",
  "name": "testtest"
}
```
若忽略 `name`，则会生成随机文件名。

4. 等待下载完成
下载完成后，会发布消息到主题 `video/download/complete`，格式如下：
```json
{
  "status": "success",
  "url": "https://test.com/wmfx.m3u8",
  "name": "video_1749464069",
  "file_path": "downloads/video_1749464069",
  "download_url": "http://127.0.0.1:3000/video_1749464069.mp4",
  "timestamp": 1749464116
}
```

## 配置

配置可以通过（按优先级增加的顺序）设置：
1. 环境变量
2. 项目根目录下的配置文件 `config.toml` 
3. 命令行参数

配置文件 `config.toml`:
```toml
[mqtt]
MQTT_BROKER = "mqtt.idev.top"
MQTT_PORT = 1883
QOS_LEVEL = 0
MQTT_TOPIC_SUBSCRIBE = "video/download/request"
MQTT_TOPIC_PUBLISH = "video/download/complete"
MQTT_CLIENT_ID = "video_downloader_client"
DOWNLOAD_DIR = "downloads"
DOWNLOAD_PREFIX_URL = ""
```

- **DOWNLOAD_PREFIX_URL** 用于替换下载文件的 URL 前缀。   
比如文件名为 `test.mp4`，如果配置了此参数值为 `http://127.0.0.1:8080/downloads/`，则下载此 MP4 视频的网址为：`http://127.0.0.1:8080/downloads/test.mp4`。配合 `nginx` 反向代理使用。

命令行参数:
```bash
uv run video-downloader --mqtt-broker mqtt.example.com --mqtt-port 1884
```

## 运行

```bash
uv run video-downloader
```

## 开发

安装开发依赖
```bash
uv sync --all-extras
```

运行测试
```bash
uv run pytest
```
