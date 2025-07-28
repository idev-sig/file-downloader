# Docker 部署

## Docker Compose
- [`compose.yml`](compose.yml)

### Docker Hub
```yaml
services:
  file-downloader:
    image: idev-sig/file-downloader:latest
    container_name: file-downloader
    restart: unless-stopped
    environment:
      - TZ=Asia/Shanghai
      - BROKER="broker.emqx.io"
      - PORT=1883
      - QOS=2
      - KEEPALIVE=60
      - TOPIC_SUBSCRIBE="file/download/request"
      - TOPIC_PUBLISH="file/download/complete"
      - CLIENT_ID="file"
      - DOWNLOAD_DIR="downloads"
      - DOWNLOAD_PREFIX_URL=""
      - USERNAME=""
      - PASSWORD=""
    volumes:
      - ./downloads:/app/downloads
