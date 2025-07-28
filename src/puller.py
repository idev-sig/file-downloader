import aria2p
import paho.mqtt.client as mqtt
import json
import subprocess
import time
import logging
import queue
import threading
from aria2s import Aria2cServer
from logger import setup_logging
from config import load_config
from utils import extract_url_from_text, is_valid_magnet_url

"""
下载到本地客户端
"""

def on_connect(client, userdata, flags, rc, *args, **kwargs):
    """MQTT 连接回调函数，兼容 MQTT 3.1/3.1.1 和 5.0"""
    logging.info(f"Connected to MQTT broker with result code {rc}")
    if rc == 0:
        # 从 userdata 获取配置
        config = userdata['config']
        client.subscribe(config['TOPIC_PUBLISH'], qos=config['QOS'])
        logging.info(f"Subscribed to topic: {config['TOPIC_PUBLISH']} with QoS {config['QOS']}")
    else:
        logging.error(f"Failed to connect to MQTT broker: {rc}")

def on_message(client, userdata, msg):
    """MQTT 消息回调函数"""
    logging.info(f"Received message on topic {msg.topic}: {msg.payload.decode()}")
    try:
        # Add message to the queue
        userdata['message_queue'].put((msg, time.time()))
        logging.info(f"Message queued for processing: {msg.payload.decode()}")
    except Exception as e:
        logging.error(f"Error queuing message: {str(e)}")

def download_file(download_url, config):
    """
    下载文件
    """
    if config['ARIA2_RPC_ENABLE']:
        download_file_aria2_rpc(download_url, config)
    else:
        download_file_aria2c_cmd(download_url, config)

def download_file_aria2_rpc(download_url, config):
    """
    使用 aria2 RPC 下载文件
    依赖 aria2c --enable-rpc
    """
    logging.info(f"Downloading file using aria2 RPC: {download_url}")
    try:
        save_dir = config.get('ARIA2_DOWNLOAD_DIR', 'aria_downloads')
        Aria2cServer(
            host=config.get('ARIA2_RPC_HOST', '127.0.0.1'),
            port=config.get('ARIA2_RPC_PORT', 6800),
            secret=config.get('ARIA2_RPC_TOKEN', ''),
            save_dir=save_dir,
        ).download(download_url, save_dir)  
    except Exception as e:
        logging.error(f"Error downloading file: {str(e)}")

def download_file_aria2c_cmd(download_url, config):
    """
    使用命令行工具下载文件
    依赖 aria2c
    """
    logging.info(f"Downloading file using aria2c: {download_url}")
    try:
        # 你可以根据需要修改命令
        command = [
            'aria2c',
            '-x', '16',
            '-d', config['ARIA2_DOWNLOAD_DIR'],
            download_url,
        ]
        
        logging.info(f"Executing command: {' '.join(command)}")
        
        # 执行下载命令
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            encoding="utf-8",          # 添加 encoding 时
            # errors="ignore",           # 忽略非法字符            
            text=True
        )
        
        if result.returncode == 0:
            logging.info("File downloaded successfully")
            return True
        else:
            logging.error(f"Failed to download file. Error: {result.stderr}")
            return None
            
    except Exception as e:
        logging.error(f"Error downloading file: {str(e)}")
        return None
    
def process_message(client, config, msg, receive_time):
    """Process a single MQTT message."""
    try:
        payload = msg.payload.decode('utf-8')
        logging.info(f"Processing message: {payload}")

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
        
        if not is_valid_magnet_url(download_url) and not extract_url_from_text(download_url):
            logging.warning(f"Invalid URL: {download_url}")
            return
            
        logging.info(f"Download URL: {download_url}")

        # 下载文件
        download_file(download_url, config)
            
    except Exception as e:
        logging.error(f"Error processing message: {str(e)}")        

def message_processor(client, userdata, stop_event):
    """Worker thread to process messages from the queue sequentially."""
    message_queue = userdata['message_queue']
    config = userdata['config']
    
    while not stop_event.is_set():
        try:
            # Get message from queue (block until a message is available or timeout)
            msg, receive_time = message_queue.get(timeout=1.0)
            logging.info("Dequeued message for processing")
            process_message(client, config, msg, receive_time)
            message_queue.task_done()
        except queue.Empty:
            continue
        except Exception as e:
            logging.error(f"Error in message processor: {str(e)}")

def on_log(client, userdata, paho_log_level, messages):
    if paho_log_level == mqtt.LogLevel.MQTT_LOG_ERR:
        print(messages)


def main():
    service_name = 'puller'

    config = load_config()
    
    # 配置参数
    BROKER = config['BROKER']
    PORT = config['PORT']
    QOS = config['QOS']
    KEEPALIVE = config['KEEPALIVE']
    # MQTT_TOPIC_SUBSCRIBE = config['MQTT_TOPIC_SUBSCRIBE']
    TOPIC_PUBLISH = config['TOPIC_PUBLISH']
    # yymmddhhiiss
    suffix = time.strftime(f"_{service_name}_%y%m%d%H%M%S", time.localtime())
    CLIENT_ID = config['CLIENT_ID'] + suffix
    # DOWNLOAD_DIR = config['DOWNLOAD_DIR']
    # DOWNLOAD_PREFIX_URL=config['DOWNLOAD_PREFIX_URL']

    USERNAME = config.get('USERNAME', None)
    PASSWORD = config.get('PASSWORD', None)

    ARIA2_SERVER_ENABLE = config.get('ARIA2_SERVER_ENABLE', False)
    ARIA2_RPC_ENABLE = config.get('ARIA2_RPC_ENABLE', False)

    ARIA2_RPC_HOST = config['ARIA2_RPC_HOST']
    ARIA2_RPC_PORT = config['ARIA2_RPC_PORT']
    ARIA2_RPC_TOKEN = config['ARIA2_RPC_TOKEN']
    ARIA2_DOWNLOAD_DIR = config['ARIA2_DOWNLOAD_DIR']

    # 确保下载目录存在
    # if not os.path.exists(DOWNLOAD_DIR):
    #     os.makedirs(DOWNLOAD_DIR)    

    # 设置日志    
    setup_logging(service_name)

    # 这里添加你的 MQTT 客户端逻辑
    print("::Configuration loaded::")
    print(f"MQTT Broker: {BROKER}:{PORT}")
    print(f"QoS Level: {QOS}")
    print(f"Subscribe Topic: {TOPIC_PUBLISH}")
    print(f"Client ID: {CLIENT_ID}")
    # print(f"Download Directory: {DOWNLOAD_DIR}")
    # print(f"Download Prefix URL: {DOWNLOAD_PREFIX_URL}")
    print(f"MQTT Username: {USERNAME}")
    print(f"MQTT Password: {PASSWORD}")
    print(f"ARIA2 Server Enable: {ARIA2_SERVER_ENABLE}")
    print(f"ARIA2 RPC Enable: {ARIA2_RPC_ENABLE}")
    print(f"ARIA2 RPC Host: {ARIA2_RPC_HOST}")
    print(f"ARIA2 RPC Port: {ARIA2_RPC_PORT}")
    print(f"ARIA2 RPC Token: {ARIA2_RPC_TOKEN}")
    print(f"ARIA2 Download Dir: {ARIA2_DOWNLOAD_DIR}")
    print()

    config['CLIENT_ID'] = CLIENT_ID
    config['USERNAME'] = USERNAME
    config['PASSWORD'] = PASSWORD

    # Create message queue and stop event
    message_queue = queue.Queue()
    stop_event = threading.Event()

    # Prepare userdata
    userdata = {
        'config': config,
        'message_queue': message_queue
    }    

    # 创建MQTT客户端
    mqttc = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=CLIENT_ID, userdata=userdata)
    mqttc.reconnect_delay_set(min_delay=1, max_delay=120)

    # 设置用户名和密码
    if USERNAME and PASSWORD:
        mqttc.username_pw_set(USERNAME, PASSWORD)
        logging.info(f"Using MQTT authentication: username={USERNAME}")

    mqttc.on_log = on_log
    mqttc.on_connect = on_connect
    mqttc.on_message = on_message    

    # Start message processor thread
    processor_thread = threading.Thread(
        target=message_processor,
        args=(mqttc, userdata, stop_event),
        daemon=True
    )
    processor_thread.start()    

    try:
        mqttc.connect(BROKER, PORT, keepalive=KEEPALIVE)  # 增加 keepalive
        logging.info(f"Connecting to MQTT broker: {BROKER}:{PORT}")
        mqttc.loop_start()  # 在后台线程运行 MQTT 循环
        while True:
            time.sleep(1)  # 主线程保持运行
    except KeyboardInterrupt:
        logging.info("Received shutdown signal, stopping...")
        stop_event.set()  # Signal the processor thread to stop            
    except Exception as e:
        logging.error(f"Failed to connect or run MQTT client: {e}")
        raise
    finally:
        stop_event.set()  # Ensure processor thread stops
        mqttc.loop_stop()  # Stop MQTT loop
        mqttc.disconnect()  # Disconnect MQTT client
        processor_thread.join()  # Wait for processor thread to finish
        logging.info("MQTT client stopped.")

if __name__ == "__main__":
    print("Starting MQTT file puller client...")
    main()
