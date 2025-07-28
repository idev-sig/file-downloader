import os
import platform
import re
from urllib.parse import urlparse

def extract_url_from_text(text):
    """Extract URL from text."""
    url_pattern = re.compile(
        r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
    )
    match = url_pattern.search(text)
    return match.group(0) if match else None

def is_valid_m3u8_url(url):
    """Validate if URL is a valid M3U8 URL."""
    try:
        url_obj = urlparse(url)
        return all([url_obj.scheme, url_obj.netloc]) and url_obj.path.endswith('.m3u8')
    except ValueError:
        return False
    
def is_valid_mp4_url(url):
    """Validate if URL is a valid MP4 URL."""
    try:
        url_obj = urlparse(url)
        return all([url_obj.scheme, url_obj.netloc]) and url_obj.path.endswith('.mp4')
    except ValueError:
        return False    

def is_valid_magnet_url(url):
    """Validate if URL is a valid magnet URL."""
    return url.startswith('magnet:')

def get_file_suffix(url):
    """Get file suffix from URL."""
    return os.path.splitext(url)[-1]

def truncate_filename(filename, max_bytes=255):
    """Truncate filename to max_bytes."""
    # 分离主文件名和扩展名
    name, ext = os.path.splitext(filename)
    
    # 系统类型判断（Windows/macOS: 按字符；Linux: 按字节）
    system = platform.system()
    if system in ['Windows', 'Darwin']:
        max_len = 255
        name_max_len = max_len - len(ext)
        if len(filename) <= max_len:
            return filename
        return name[:name_max_len] + ext
    else:
        # Linux/ext4: 按字节截取
        name_bytes = name.encode('utf-8')
        ext_bytes = ext.encode('utf-8')
        max_name_bytes = max_bytes - len(ext_bytes)

        # 截断 name_bytes 到 max_name_bytes
        truncated_name = b''
        for char in name:
            char_bytes = char.encode('utf-8')
            if len(truncated_name) + len(char_bytes) > max_name_bytes:
                break
            truncated_name += char_bytes

        return truncated_name.decode('utf-8', errors='ignore') + ext