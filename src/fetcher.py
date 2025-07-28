import aria2p
import paho.mqtt.client as mqtt
import json
import subprocess
import os
import time
import logging
import queue
import threading
from aria2s import Aria2cServer
from logger import setup_logging
from config import load_config
from utils import extract_url_from_text, get_file_suffix, is_valid_m3u8_url, is_valid_magnet_url

"""
Download files to a cloud server with sequential MQTT message processing.
（此版本为 AI 优化，支持队列）
"""

def on_connect(client, userdata, flags, rc, *args, **kwargs):
    """MQTT connection callback, compatible with MQTT 3.1/3.1.1 and 5.0."""
    logging.info(f"Connected to MQTT broker with result code {rc}")
    if rc == 0:
        config = userdata['config']
        client.subscribe(config['TOPIC_SUBSCRIBE'], qos=config['QOS'])
        logging.info(f"Subscribed to topic: {config['TOPIC_SUBSCRIBE']} with QoS {config['QOS']}")
    else:
        logging.error(f"Failed to connect to MQTT broker: {rc}")

def on_message(client, userdata, msg):
    """MQTT message callback: Add messages to the queue for sequential processing."""
    logging.info(f"Received message on topic {msg.topic}: {msg.payload.decode()}")
    try:
        # Add message to the queue
        userdata['message_queue'].put((msg, time.time()))
        logging.info(f"Message queued for processing: {msg.payload.decode()}")
    except Exception as e:
        logging.error(f"Error queuing message: {str(e)}")


def download_file(ftype, url, output, save_dir, aria2server):
    """Download file using m3u8-downloader."""
    if ftype == "m3u8":
        return download_file_m3u8(url, output.replace(".mp4", ""), save_dir)
    else:
        # 如果不是磁力链接，则判断 output 后缀是否与 url 的后缀相同，若不同，则以 url 的文件后缀为准
        if not is_valid_magnet_url(url):
            url_suffix = get_file_suffix(url)
            file_suffix = get_file_suffix(output)
            if url_suffix != file_suffix:
                output += url_suffix
        return download_file_aria2(url, output, save_dir, aria2server)
    
def download_file_aria2(url, output, save_dir, aria2server: Aria2cServer):
    """
    使用 aria2 RPC 下载文件
    依赖 aria2c --enable-rpc
    """
    logging.info(f"Downloading file using aria2 RPC: {url}")
    try:
        return aria2server.download(url, save_dir, output)  
    except Exception as e:
        logging.error(f"Error downloading file: {str(e)}")    

def download_file_m3u8(url, output, save_dir = ""):
    """Download file using m3u8-downloader."""
    try:
        command = ['m3u8-downloader', '-u', url, '-o', output]
        if save_dir:
            command.extend(['-sp', save_dir])
        logging.info(f"Executing command: {' '.join(command)}")
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            encoding="utf-8",
            # errors="ignore",
            text=True
        )
        if result.returncode == 0:
            logging.info(f"file downloaded successfully to {output}")
            return output + ".mp4"
        else:
            logging.error(f"Failed to download file. Error: {result.stderr}")
            return None
    except Exception as e:
        logging.error(f"Error downloading file: {str(e)}")
        return None

def process_message(client, config, aria2server, msg, receive_time):
    """Process a single MQTT message."""
    try:
        payload = msg.payload.decode('utf-8')
        logging.info(f"Processing message: {payload}")
        
        # Parse message content
        try:
            data = json.loads(payload)
            url = data.get('url')
            name = data.get('name')
        except json.JSONDecodeError:
            url = extract_url_from_text(payload)
            name = None
        
        if not url:
            logging.warning("No valid URL found in the message")
            return
        
        file_type = None
        if is_valid_m3u8_url(url):
            file_type = "m3u8"
        elif is_valid_magnet_url(url):
            file_type = "magnet"
        elif extract_url_from_text(url):
            file_type = "http"
        else:
            logging.warning(f"Invalid protocol for URL: {url}")
            return

        logging.info(f"Extracted URL: {url}, Name: {name}")
        
        filename = name or f"file_{int(time.time())}"
        # 防止文件名过长，不合法
        filename = filename[:100]

        file_path = download_file(file_type, url, filename, config['DOWNLOAD_DIR'], aria2server)
        if file_path:
            download_http_url = ""
            if not is_valid_magnet_url(url) and config.get('DOWNLOAD_PREFIX_URL'):
                download_http_url = f"{config['DOWNLOAD_PREFIX_URL']}{file_path}"

            # Publish success message
            complete_msg = {
                "status": "success",
                "url": url,
                "name": name if name else '',
                "file_path": file_path,
                "download_url": ''.join(download_http_url),
                "timestamp": int(time.time()),
                "receive_time": receive_time
            }
            # print(complete_msg)
            result = client.publish(
                config['TOPIC_PUBLISH'],
                json.dumps(complete_msg, ensure_ascii=False),
                qos=config['QOS']
            )
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                logging.info(f"Published completion message for {url}")
            else:
                logging.error(f"Failed to publish completion message: {result.rc}")
        else:
            # Publish error message
            error_msg = {
                "status": "error",
                "url": url,
                "name": filename,
                "message": "Failed to download file",
                "timestamp": int(time.time()),
                "receive_time": receive_time
            }
            result = client.publish(
                config['TOPIC_PUBLISH'],
                json.dumps(error_msg, ensure_ascii=False),
                qos=config['QOS']
            )
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                logging.info(f"Published error message for {url}")
            else:
                logging.error(f"Failed to publish error message: {result.rc}")
                
    except Exception as e:
        logging.error(f"Error processing message: {str(e)}")

def message_processor(client, userdata, stop_event):
    """Worker thread to process messages from the queue sequentially."""
    message_queue = userdata['message_queue']
    config = userdata['config']
    aria2c_server = userdata['aria2server']
    
    while not stop_event.is_set():
        try:
            # Get message from queue (block until a message is available or timeout)
            msg, receive_time = message_queue.get(timeout=1.0)
            logging.info("Dequeued message for processing")
            process_message(client, config, aria2c_server, msg, receive_time)
            message_queue.task_done()
        except queue.Empty:
            continue
        except Exception as e:
            logging.error(f"Error in message processor: {str(e)}")

def on_log(client, userdata, paho_log_level, messages):
    """Log MQTT client errors."""
    if paho_log_level == mqtt.LogLevel.MQTT_LOG_ERR:
        print(messages)

def main():
    service_name = "fetcher"
    
    # Load configuration
    config = load_config()
    
    # Configuration parameters
    BROKER = config['BROKER']
    PORT = config['PORT']
    QOS = config['QOS']
    KEEPALIVE = config['KEEPALIVE']
    TOPIC_SUBSCRIBE = config['TOPIC_SUBSCRIBE']
    TOPIC_PUBLISH = config['TOPIC_PUBLISH']
    suffix = time.strftime(f"_{service_name}_%y%m%d%H%M%S", time.localtime())
    CLIENT_ID = config['CLIENT_ID'] + suffix
    DOWNLOAD_DIR = config['DOWNLOAD_DIR']
    DOWNLOAD_PREFIX_URL = config['DOWNLOAD_PREFIX_URL']
    USERNAME = config.get('USERNAME', None)
    PASSWORD = config.get('PASSWORD', None)

    # Ensure download directory exists
    if not os.path.exists(DOWNLOAD_DIR):
        os.makedirs(DOWNLOAD_DIR)

    # Setup logging
    setup_logging("fetcher")

    # Print configuration
    print("::Configuration loaded::")
    print(f"MQTT Broker: {BROKER}:{PORT}")
    print(f"QoS Level: {QOS}")
    print(f"Subscribe Topic: {TOPIC_SUBSCRIBE}")
    print(f"Publish Topic: {TOPIC_PUBLISH}")
    print(f"Client ID: {CLIENT_ID}")
    print(f"Download Directory: {DOWNLOAD_DIR}")
    print(f"Download Prefix URL: {DOWNLOAD_PREFIX_URL}")
    print()

    # Create message queue and stop event
    message_queue = queue.Queue()
    stop_event = threading.Event()

    # Start aria2c server
    aria2c_server = Aria2cServer(
        host=config.get('ARIA2_RPC_HOST', '127.0.0.1'),
        port=config.get('ARIA2_RPC_PORT', 6800),
        secret=config.get('ARIA2_RPC_TOKEN', ''),
        save_dir=config.get('DOWNLOAD_DIR', 'downloads')
    )
    aria2c_server.start()

    # Prepare userdata
    userdata = {
        'config': config,
        'message_queue': message_queue,
        'aria2server': aria2c_server,
    }

    # Create MQTT client
    mqttc = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=CLIENT_ID, userdata=userdata)
    mqttc.reconnect_delay_set(min_delay=1, max_delay=120)

    # Set username and password if provided
    if USERNAME and PASSWORD:
        mqttc.username_pw_set(USERNAME, PASSWORD)
        logging.info(f"Using MQTT authentication: username={USERNAME}")

    # Set callbacks
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
        # Connect to MQTT broker
        mqttc.connect(BROKER, PORT, keepalive=KEEPALIVE)
        logging.info(f"Connecting to MQTT broker: {BROKER}:{PORT}")
        mqttc.loop_start()  # Start MQTT loop in background thread
        while True:
            time.sleep(1)  # Keep main thread alive
    except KeyboardInterrupt:
        logging.info("Received shutdown signal, stopping...")
        stop_event.set()  # Signal the processor thread to stop
    except Exception as e:
        logging.error(f"Failed to connect or run MQTT client: {e}")
        raise
    finally:
        aria2c_server.stop()
        stop_event.set()  # Ensure processor thread stops
        mqttc.loop_stop()  # Stop MQTT loop
        mqttc.disconnect()  # Disconnect MQTT client
        processor_thread.join()  # Wait for processor thread to finish
        logging.info("MQTT client stopped.")

if __name__ == "__main__":
    print("Starting MQTT file fetcher client...")
    main()