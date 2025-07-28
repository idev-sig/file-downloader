import logging
import os
import subprocess
import aria2p


class Aria2cServer:
    def __init__(self, host="http://localhost", port=6800, secret="", save_dir=""):
        self.debug = False
        self.host = host
        self.port = port
        self.secret = secret
        self.save_dir = self._real_save_dir(save_dir)
        self.process = None
        self._client = None

    def _real_save_dir(self, save_dir: str):
        """Get the real save directory."""
        if save_dir:
            # If save_dir is an absolute path, return it as is
            if os.path.isabs(save_dir):
                return save_dir
            # For relative paths, join with the current working directory
            return os.path.join(os.getcwd(), save_dir)
        # Return current working directory if save_dir is empty
        return os.getcwd()

    def client(self):
        """Get or create aria2p client instance."""
        if self._client is None:
            self._client = aria2p.Client(
                host=self.host,
                port=self.port,
                secret=self.secret,
                timeout=5
            )
        return self._client

    def is_running(self):
        """Check if aria2c server is running."""
        try:
            # 尝试连接到 RPC 服务
            client = self.client()
            # 调用一个简单的 RPC 方法来测试连接
            client.get_version()
            return True
        except (aria2p.client.ClientException, ConnectionError, Exception):
            return False

    def start(self):
        """Start aria2c server."""
        # 先检查是否已经运行
        if self.is_running():
            logging.info("aria2c server is already running")
            return True
        
        try:
            # listen_all = "true" if self.host == '0.0.0.0' else "false"

            command = [
                'aria2c', 
                '--enable-rpc', 
                f'--rpc-listen-port={self.port}',
                f'--rpc-listen-all=true', 
                f'--rpc-secret={self.secret}', 
                f'--dir={self.save_dir}', 
                '--daemon=true',
            ]

            if self.debug:
                command.append('--log=./aria2.log')
                command.append('--log-level=debug')

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
                logging.info("aria2c server started successfully")
                return True
            else:
                logging.error(f"Failed to start aria2c server. Error: {result.stderr}")
                return False
        except Exception as e:
            logging.error(f"Error starting aria2c server: {str(e)}")
            return False

    def stop(self):
        """Stop the aria2c server using aria2p."""
        
        try:
            result = self.client().shutdown()
            if result:
                logging.info("aria2c server shutdown request sent successfully")
                self._client = None
                return True
            else:
                logging.error("Failed to send shutdown request")
                return False

        except aria2p.client.ClientException as e:
            logging.error(f"Failed to connect to aria2c RPC for shutdown: {str(e)}")
            return False
        except Exception as e:
            logging.error(f"Error stopping aria2c server: {str(e)}")
            return False

    def download(self, download_url, save_dir="", filename=""):
        """使用 aria2 RPC 下载文件"""
        logging.info(f"Starting download: {download_url}")
        
        try:
            self.is_running()

            aria2 = aria2p.API(self._client)
            
            options = {}
            if save_dir:
                options['dir'] = self._real_save_dir(save_dir)
            if filename:
                options['out'] = filename
                
            download = aria2.add_uris([download_url], options=options)
            logging.info(f"Download added successfully: {download_url}")
            return download.name
            
        except Exception as e:
            error_msg = f"Error adding download to aria2 RPC: {str(e)}"
            logging.error(error_msg)
            raise ValueError(error_msg)
