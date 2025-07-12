# Docker 部署

## Docker Compose
- [`compose.yml`](compose.yml)

### Docker Hub
```yaml
services:
  video-downloader:
    image: idevsig/video-downloader:latest
    container_name: video-downloader
    restart: unless-stopped
    environment:
      - TZ=Asia/Shanghai
      - MQTT_BROKER="broker.emqx.io"
      - MQTT_PORT=1883
      - QOS_LEVEL=2
      - KEEPALIVE=60
      - TOPIC_SUBSCRIBE="video/download/request"
      - TOPIC_PUBLISH="video/download/complete"
      - CLIENT_ID="video"
      - DOWNLOAD_DIR="downloads"
      - DOWNLOAD_PREFIX_URL=""
      - MQTT_USERNAME=""
      - MQTT_PASSWORD=""
    volumes:
      - ./downloads:/app/downloads
