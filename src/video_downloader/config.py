import os
import toml
import argparse

def load_config():
    """加载配置，优先级：命令行参数 > 配置文件 > 环境变量 > 默认值"""
    # 默认配置
    default_config = {
        'MQTT_BROKER': 'test.mosquitto.org',
        'MQTT_PORT': 1883,
        'QOS_LEVEL': 0,
        'MQTT_TOPIC_SUBSCRIBE': 'video/download/request',
        'MQTT_TOPIC_PUBLISH': 'video/download/complete',
        'MQTT_CLIENT_ID': 'video_downloader_client',
        'DOWNLOAD_DIR': 'downloads',
        "DOWNLOAD_PREFIX_URL": "",
    }

    # 初始化配置为默认值
    config = default_config.copy()

    # 1. 获取环境变量（最低优先级）
    for key in default_config:
        env_value = os.getenv(key)
        if env_value is not None:
            # 对端口和QoS级别进行类型转换
            if key == 'MQTT_PORT' or key == 'QOS_LEVEL':
                try:
                    config[key] = int(env_value)
                except ValueError:
                    print(f"警告: 无效的环境变量 {key}: {env_value}")
            else:
                config[key] = env_value

    # 2. 加载配置文件（覆盖环境变量）
    config_file = 'config.toml'
    if os.path.exists(config_file):
        try:
            with open(config_file, 'r') as f:
                file_config = toml.load(f)
                # 更新配置，使用大写键名直接从 [mqtt] 部分获取
                mqtt_section = file_config.get('mqtt', {})
                for key in default_config:
                    if key in mqtt_section:
                        config[key] = mqtt_section[key]
        except Exception as e:
            print(f"警告: 无法加载配置文件 {config_file}: {e}")

    # 3. 解析命令行参数（最高优先级）
    parser = argparse.ArgumentParser(description='Video Downloader MQTT Client')
    parser.add_argument('--mqtt-broker', help='MQTT Broker address')
    parser.add_argument('--mqtt-port', type=int, help='MQTT Broker port')
    parser.add_argument('--qos-level', type=int, help='QoS level')
    parser.add_argument('--subscribe-topic', help='MQTT subscribe topic')
    parser.add_argument('--publish-topic', help='MQTT publish topic')
    parser.add_argument('--client-id', help='MQTT client ID')
    parser.add_argument('--download-dir', help='Download directory')
    parser.add_argument('--download-prefix-url', help='Download prefix URL')
    
    args = parser.parse_args()

    # 更新配置
    for key in default_config:
        arg_key = key.lower().replace('-', '_')
        arg_value = getattr(args, arg_key, None)
        if arg_value is not None:
            config[key] = arg_value

    return config