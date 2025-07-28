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

def truncate_filename(filename: str, max_bytes=230) -> str:
    name, ext = os.path.splitext(filename)

    system = platform.system()
    if system in ['Windows', 'Darwin']:  # Windows/macOS: 按字符计数
        max_chars = 255 - len(ext)
        if len(filename) <= 255:
            return filename
        return name[:max_chars] + ext
    else:
        # Linux/ext4: 按 UTF-8 字节计数
        name_bytes = name.encode('utf-8')
        ext_bytes = ext.encode('utf-8')
        max_name_bytes = max_bytes - len(ext_bytes)

        # 截取字节，保留完整 UTF-8 字符
        truncated_name_bytes = name_bytes[:max_name_bytes]
        safe_name = truncated_name_bytes.decode('utf-8', errors='ignore')
        return safe_name + ext