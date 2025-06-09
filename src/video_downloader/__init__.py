import paho.mqtt.client as mqtt
import json
import re
import subprocess
import os
from urllib.parse import urlparse
import time
import logging
from .config import load_config

def on_connect(client, userdata, flags, rc, *args, **kwargs):
    """MQTT 连接回调函数，兼容 MQTT 3.1/3.1.1 和 5.0"""
    logging.info(f"Connected to MQTT broker with result code {rc}")
    if rc == 0:
        # 从 userdata 获取配置
        config = userdata
        client.subscribe(config['MQTT_TOPIC_SUBSCRIBE'], qos=config['QOS_LEVEL'])
        logging.info(f"Subscribed to topic: {config['MQTT_TOPIC_SUBSCRIBE']} with QoS {config['QOS_LEVEL']}")
    else:
        logging.error(f"Failed to connect to MQTT broker: {rc}")

def on_message(client, userdata, msg):
    """MQTT 消息回调函数"""
    logging.info(f"Received message on topic {msg.topic}: {msg.payload.decode()}")
    
    try:
        # 解析消息内容
        payload = msg.payload.decode('utf-8')
        name = None
        logging.info(f"Received message: {payload}")
        
        # 尝试解析为JSON
        try:
            data = json.loads(payload)
            url = data.get('url')
            name = data.get('name')
        except json.JSONDecodeError:
            # 如果不是JSON，尝试直接提取URL
            url = extract_url_from_text(payload)
        
        if not url:
            logging.warning("No valid URL found in the message")
            return
            
        logging.info(f"Extracted URL: {url}")
        logging.info(f"Name: {name}")

        config = userdata
        
        filename = name or "video_" + str(int(time.time()))
        output_path = os.path.join(config['DOWNLOAD_DIR'], filename)
        download_url = f"{config['DOWNLOAD_PREFIX_URL']}{filename}.mp4"

        # 下载视频
        video_path = download_video(url, output_path)
        # video_path = output_path
        
        if video_path:
            # 发布下载完成消息
            complete_msg = {
                "status": "success",
                "url": url,
                "name": filename,
                "file_path": video_path,
                "download_url": download_url,
                "timestamp": int(time.time())
            }
            # 从 userdata 获取配置
            config = userdata           
            client.publish(config['MQTT_TOPIC_PUBLISH'], json.dumps(complete_msg), qos=config['QOS_LEVEL'])
            logging.info(f"Published completion message for {url}")
        else:
            error_msg = {
                "status": "error",
                "url": url,
                "name": filename,
                "message": "Failed to download video",
                "timestamp": int(time.time())
            }
            client.publish(config['MQTT_TOPIC_PUBLISH'], json.dumps(error_msg), qos=config['QOS_LEVEL'])
            logging.info(f"Published error message for {url}")
            
    except Exception as e:
        logging.error(f"Error processing message: {str(e)}")

def extract_url_from_text(text):
    """从文本中提取URL"""
    # 简单的URL正则匹配
    url_pattern = re.compile(
        r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
    )
    match = url_pattern.search(text)
    return match.group(0) if match else None

def is_valid_m3u8_url(url):
    """验证URL是否为有效的 M3U8 URL"""
    try:
        url_obj = urlparse(url)
        return all([url_obj.scheme, url_obj.netloc]) and url_obj.path.endswith('.m3u8')
    except ValueError:
        return False

def download_video(url, output_path):
    """使用命令行工具下载视频"""
    try:
        # 你可以根据需要修改命令
        command = [
            'm3u8-downloader',
            '-u', url,
            '-o', output_path,
        ]
        
        logging.info(f"Executing command: {' '.join(command)}")
        
        # 执行下载命令
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            encoding="utf-8",          # 添加 encoding 时
            errors="ignore",           # 忽略非法字符            
            text=True
        )
        
        if result.returncode == 0:
            logging.info(f"Video downloaded successfully to {output_path}")
            return output_path
        else:
            logging.error(f"Failed to download video. Error: {result.stderr}")
            return None
            
    except Exception as e:
        logging.error(f"Error downloading video: {str(e)}")
        return None
    
def on_log(client, userdata, paho_log_level, messages):
    if paho_log_level == mqtt.LogLevel.MQTT_LOG_ERR:
        print(messages)

def setup_logging():
    """配置日志记录"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        # format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler("video_downloader.log"),
            logging.StreamHandler()
        ]
    )

def main():
    config = load_config()
    
    # 配置参数
    MQTT_BROKER = config['MQTT_BROKER']
    MQTT_PORT = config['MQTT_PORT']
    QOS_LEVEL = config['QOS_LEVEL']
    MQTT_TOPIC_SUBSCRIBE = config['MQTT_TOPIC_SUBSCRIBE']
    MQTT_TOPIC_PUBLISH = config['MQTT_TOPIC_PUBLISH']
    # yymmddhhiiss
    nowTime = time.strftime("_%y%m%d%H%M%S", time.localtime())
    MQTT_CLIENT_ID = config['MQTT_CLIENT_ID'] + nowTime
    DOWNLOAD_DIR = config['DOWNLOAD_DIR']
    DOWNLOAD_PREFIX_URL=config['DOWNLOAD_PREFIX_URL']

    # 确保下载目录存在
    if not os.path.exists(DOWNLOAD_DIR):
        os.makedirs(DOWNLOAD_DIR)    

    # 设置日志    
    setup_logging()

    # 这里添加你的 MQTT 客户端逻辑
    print("Configuration loaded:")
    print(f"MQTT Broker: {MQTT_BROKER}:{MQTT_PORT}")
    print(f"QoS Level: {QOS_LEVEL}")
    print(f"Subscribe Topic: {MQTT_TOPIC_SUBSCRIBE}")
    print(f"Publish Topic: {MQTT_TOPIC_PUBLISH}")
    print(f"Client ID: {MQTT_CLIENT_ID}")
    print(f"Download Directory: {DOWNLOAD_DIR}")
    print(f"Download Prefix URL: {DOWNLOAD_PREFIX_URL}")
    print()

    # 创建MQTT客户端
    mqttc = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=MQTT_CLIENT_ID, userdata=config)
    mqttc.on_log = on_log
    mqttc.on_connect = on_connect
    mqttc.on_message = on_message    

    # 连接MQTT服务器
    try:
        mqttc.connect(MQTT_BROKER, MQTT_PORT, 60)
    except Exception as e:
        logging.error(f"Failed to connect to MQTT broker: {str(e)}")
        return
    
    # 保持连接
    mqttc.loop_forever()    

if __name__ == "__main__":
    print("Starting MQTT video downloader client...")
    main()
