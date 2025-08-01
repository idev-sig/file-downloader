# 云端文件下载器

## 介绍
本项目是基于 MQTT 的云端文件下载器。

## 先决条件
1. 安装 [uv](https://github.com/astral-sh/uv)。 
    ```bash
    # On macOS and Linux.
    curl -LsSf https://astral.sh/uv/install.sh | sh
    ```
2. 安装 [`m3u8-downloader`](https://github.com/forkdo/m3u8-downloader)（下载至服务器）。
    ```bash
    curl -L https://s.fx4.cn/m3u8-downloader | bash
    ```
3. 安装 [aria2c](https://github.com/aria2/aria2)。

## 安装

1. 拉取代码并进入项目目录：
   ```bash
   git clone <repository-url>
   cd file-downloader
   ```
2. 安装依赖：
   ```bash
   uv sync
   ```
   
## 使用

### 基于源码部署
1. 启动 MQTT 服务器
    > EMQX 配置客户端认证功能：访问控制 -> 客户端认证 -> 创建 -> Password-Based -> 内置数据库 -> 键入“用户名、密码” -> 保存。
2. 启动本服务
    ```bash
    uv sync
    uv run fetcher
    ```
3. 使用客户端，发布消息（`JSON`）到主题 `file/download/request`，格式如下：   
建议 `QOS` 为 `0`, `retain` 为 `false`。若 `retain` 为 `true`，则消息会被保留，直到有新的消息发布到相同的主题。会导致重启服务器后，重复下载相同的文件。
    ```bash
    {
      "url": "https://test.com/50941.m3u8",
      "name": "testtest"
    }
    ```
    若忽略 `name`，则会生成随机文件名。

4. 等待下载完成   
下载完成后，会发布消息到主题 `file/download/complete`，格式如下：
    ```json
    {
      "status": "success",
      "url": "https://test.com/wmfx.m3u8",
      "name": "file_1749464069",
      "file_path": "downloads/file_1749464069",
      "download_url": "http://127.0.0.1:3000/file_1749464069.mp4",
      "timestamp": 1749464116
    }
    ```

5. 同步下载到本地客户端   
  当服务器端下载 M3U8 视频，且合并为 MP4 视频后，本地客户端同步下载至本地。
    ```bash
    uv sync
    uv run puller    
    ```

### 基于 Docker 部署

- 自构建
    ```bash
     # 构建 
     docker buildx bake
    ```

    **服务端**
    ```bash
     # 运行
     docker run -d -v $(pwd)/downloads:/app/downloads --name file-downloader file-downloader:local

     # 使用环境变量
     docker run -d -v $(pwd)/downloads:/app/downloads -e DOWNLOAD_PREFIX_URL="http://127.0.0.1:8080/" --name file-downloader file-downloader:local
    ```

    **客户端**
    ```bash
     # 使用外置的 aria2 下载视频
     docker run -e ARIA2_RPC_HOST=http://192.168.1.138 -e ARIA2_DOWNLOAD_DIR=test_down -it file-downloader:local puller --qos 2 --aria2-rpc-token your-secret-key --aria2-rpc-enable 1 --aria2-rpc-download-dir test_download
    
     # 挂载下载目录
     docker run -e ARIA2_DOWNLOAD_DIR=test_down -e QOS=2 -v $(pwd)/aria2down:/app/test_down -it file-downloader:local puller

     # aria2c rpc server
     aria2c --enable-rpc --rpc-listen-all=true --rpc-secret=your-secret-key --dir=/downloads
    ```

- 基于 Docker Compose
使用 [**`Docker Compose`**](docker/README.md) 部署，请查阅 `docker/README.md`。

- 使用项目提供的 Docker 镜像

    > **版本：** `latest`, `main`, <`TAG`>

    | Registry                                                                                   | Image                                                  |
    | ------------------------------------------------------------------------------------------ | ------------------------------------------------------ |
    | [**Docker Hub**](https://hub.docker.com/r/idevsig/file-downloader/)                                | `idevsig/file-downloader`                                    |
    | [**GitHub Container Registry**](https://github.com/idev-sig/file-downloader/pkgs/container/file-downloader) | `ghcr.io/idevsig/file-downloader`                            |
    | **Tencent Cloud Container Registry**                                                       | `ccr.ccs.tencentyun.com/idevsig/file-downloader`             |
    | **Aliyun Container Registry**                                                              | `registry.cn-guangzhou.aliyuncs.com/idevsig/file-downloader` |

## 配置

配置可以通过（按优先级增加的顺序）设置：
1. 环境变量
2. 项目根目录下的配置文件 `config.toml` 
3. 命令行参数

配置文件 `config.toml`:
```toml
[mqtt]
BROKER = "mqtt.eclipseprojects.io"
PORT = 1883
QOS = 0
TOPIC_SUBSCRIBE = "file/download/request"
TOPIC_PUBLISH = "file/download/complete"
CLIENT_ID = "file_downloader_client"
DOWNLOAD_DIR = "downloads"
DOWNLOAD_PREFIX_URL = ""
USERNAME = ""
PASSWORD = ""

[aria2]
ARIA2_SERVER_ENABLE = 0
ARIA2_RPC_ENABLE = 0
ARIA2_RPC_HOST = "http://localhost"
ARIA2_RPC_PORT = 6800
ARIA2_RPC_TOKEN = "your-secret-key"
ARIA2_DOWNLOAD_DIR = "aria_downloads"
```

- **DOWNLOAD_PREFIX_URL** 用于替换下载文件的 URL 前缀。   
比如文件名为 `test.mp4`，如果配置了此参数值为 `http://127.0.0.1:8080/downloads/`，则下载此 MP4 视频的网址为：`http://127.0.0.1:8080/downloads/test.mp4`。配合 `nginx` 反向代理使用。

命令行参数:
```bash
uv run fetcher --mqtt-broker mqtt.example.com --mqtt-port 1884
```

## 运行

```bash
uv run fetcher
```

```mermaid
flowchart TD
    A[客户端A] -- 发布下载请求到主题 file/download/request --> M[MQTT 服务器]
    subgraph VPS 服务器
        direction TB
        S1[订阅 file/download/request]
        S2[解析请求消息，提取 M3U8/HTTP/MAGNET 地址]
        S3[使用 m3u8-downloader 工具]
        S4[下载 M3U8 片段]
        S5[将 M3U8 的 TS 片段合成 MP4]
        S6[生成 HTTP 下载地址发送到主题 file/download/complete]
        S7[下载 HTTP 文件]
        S8[下载 MAGNET 文件]
        S9[使用 aria2c 工具]
        
        S1 --> S2
        S2 -->|M3U8| S3 --> S4 --> S5 --> S6
        S2 -->|HTTP| S9 --> S7 --> S6
        S2 -->|MAGNET| S9 --> S8
    end
    M -- 消息推送到订阅方 --> S1

    S6 --> M2[MQTT 服务器]

    M2 -- 将 HTTP 地址消息发布到主题 file/download/complete --> B[客户端B【可选】]
    B -- 通过本地 aria2c CL工具--> L[下载保存文件]
    B -- 通过调用 aria2c RPC 服务 --> L
```

## 仓库镜像

- https://git.jetsung.com/idev/file-downloader
- https://framagit.org/idev/file-downloader
- https://gitcode.com/idev/file-downloader
- https://github.com/idev-sig/file-downloader
