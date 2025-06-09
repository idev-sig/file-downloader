import paho.mqtt.client as mqtt
import json
import re
import subprocess
import os
from urllib.parse import urlparse
import time
import logging
from .config import load_config

"""
下载到本地客户端
"""

def on_connect(client, userdata, flags, rc, *args, **kwargs):
    """MQTT 连接回调函数，兼容 MQTT 3.1/3.1.1 和 5.0"""
    logging.info(f"Connected to MQTT broker with result code {rc}")
    if rc == 0:
        # 从 userdata 获取配置
        config = userdata
        client.subscribe(config['MQTT_TOPIC_PUBLISH'], qos=config['QOS_LEVEL'])
        logging.info(f"Subscribed to topic: {config['MQTT_TOPIC_PUBLISH']} with QoS {config['QOS_LEVEL']}")
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
            download_url = data.get('download_url')
        except json.JSONDecodeError:
            # 如果不是JSON，尝试直接提取URL
            download_url = extract_url_from_text(payload)
        
        if not download_url:
            logging.warning("No valid URL found in the message")
            return
        
        if not is_valid_mp4_url(download_url):
            logging.warning(f"Invalid MP4 URL: {download_url}")
            return
            
        logging.info(f"Download URL: {download_url}")

        # 下载视频
        download_video(download_url)
            
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

def is_valid_mp4_url(url):
    """验证URL是否为有效的 MP4 URL"""
    try:
        url_obj = urlparse(url)
        return all([url_obj.scheme, url_obj.netloc]) and url_obj.path.endswith('.mp4')
    except ValueError:
        return False

def download_video(download_url):
    """
    使用命令行工具下载视频
    依赖 aria2c
    """
    try:
        # 你可以根据需要修改命令
        command = [
            'aria2c',
            '-x', '16',
            download_url,
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
            logging.info("Video downloaded successfully")
            return True
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

    # 确保下载目录存在
    log_path = "logs"
    if not os.path.exists(log_path):
        os.makedirs(log_path)   

    output_path = os.path.join(log_path, 'video_puller.log')

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        # format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(output_path),
            logging.StreamHandler()
        ]
    )

def main():
    config = load_config()
    
    # 配置参数
    MQTT_BROKER = config['MQTT_BROKER']
    MQTT_PORT = config['MQTT_PORT']
    QOS_LEVEL = config['QOS_LEVEL']
    # MQTT_TOPIC_SUBSCRIBE = config['MQTT_TOPIC_SUBSCRIBE']
    MQTT_TOPIC_PUBLISH = config['MQTT_TOPIC_PUBLISH']
    # yymmddhhiiss
    suffix = time.strftime("_puller_%y%m%d%H%M%S", time.localtime())
    MQTT_CLIENT_ID = config['MQTT_CLIENT_ID'] + suffix
    # DOWNLOAD_DIR = config['DOWNLOAD_DIR']
    # DOWNLOAD_PREFIX_URL=config['DOWNLOAD_PREFIX_URL']

    MQTT_USERNAME = config.get('MQTT_USERNAME', None)
    MQTT_PASSWORD = config.get('MQTT_PASSWORD', None)

    # 确保下载目录存在
    # if not os.path.exists(DOWNLOAD_DIR):
    #     os.makedirs(DOWNLOAD_DIR)    

    # 设置日志    
    setup_logging()

    # 这里添加你的 MQTT 客户端逻辑
    print("Configuration loaded:")
    print(f"MQTT Broker: {MQTT_BROKER}:{MQTT_PORT}")
    print(f"QoS Level: {QOS_LEVEL}")
    print(f"Subscribe Topic: {MQTT_TOPIC_PUBLISH}")
    print(f"Client ID: {MQTT_CLIENT_ID}")
    # print(f"Download Directory: {DOWNLOAD_DIR}")
    # print(f"Download Prefix URL: {DOWNLOAD_PREFIX_URL}")
    print()

    # 创建MQTT客户端
    mqttc = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=MQTT_CLIENT_ID, userdata=config)
    mqttc.reconnect_delay_set(min_delay=1, max_delay=120)

# 设置用户名和密码
    if MQTT_USERNAME and MQTT_PASSWORD:
        mqttc.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
        logging.info(f"Using MQTT authentication: username={MQTT_USERNAME}")

    mqttc.on_log = on_log
    mqttc.on_connect = on_connect
    mqttc.on_message = on_message    

    try:
        mqttc.connect(MQTT_BROKER, MQTT_PORT, keepalive=300)  # 增加 keepalive
        logging.info(f"Connecting to MQTT broker: {MQTT_BROKER}:{MQTT_PORT}")
        mqttc.loop_start()  # 在后台线程运行 MQTT 循环
        while True:
            time.sleep(1)  # 主线程保持运行
    except Exception as e:
        logging.error(f"Failed to connect or run MQTT client: {e}")
        raise
    finally:
        mqttc.loop_stop()  # 停止后台循环 

if __name__ == "__main__":
    print("Starting MQTT video puller client...")
    main()
