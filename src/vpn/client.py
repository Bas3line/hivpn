import socket
import struct
import select
import logging
import os
import subprocess

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class VPNClient:
    def __init__(self, server_host: str, server_port: int, password: str):
        self.server_host = server_host
        self.server_port = server_port
        self.password = password
        self.running = False
        self.tun = None
        self.original_routes = []

    def save_routes(self):
        try:
            result = subprocess.run('ip route show', shell=True, capture_output=True, text=True)
            self.original_routes = result.stdout.strip().split('\n')
            logging.info("Saved original routes")
        except:
            pass

    def restore_routes(self):
        try:
            if self.tun:
                os.system('ip link set tun0 down 2>/dev/null')
                os.system('ip link delete tun0 2>/dev/null')

            os.system('ip route flush cache')
            logging.info("Network routes restored")
        except Exception as e:
            logging.error(f"Error restoring routes: {e}")

    def create_tun(self, name: str = 'tun0'):
        import fcntl

        TUNSETIFF = 0x400454ca
        IFF_TUN = 0x0001
        IFF_NO_PI = 0x1000

        try:
            tun = open('/dev/net/tun', 'r+b', buffering=0)
            ifr = struct.pack('16sH', name.encode(), IFF_TUN | IFF_NO_PI)
            fcntl.ioctl(tun, TUNSETIFF, ifr)

            os.system(f'ip addr flush dev {name} 2>/dev/null')
            os.system(f'ip addr add 10.8.0.2/24 dev {name}')
            os.system(f'ip link set {name} up')
            os.system(f'ip route add default via 10.8.0.1 dev {name} metric 50')

            logging.info(f"TUN interface {name} created with IP 10.8.0.2/24")
            return tun
        except Exception as e:
            logging.error(f"Failed to create TUN interface: {e}")
            raise

    def authenticate(self, sock: socket.socket) -> bool:
        try:
            sock.send(self.password.encode())
            sock.settimeout(10)
            response = sock.recv(1024)
            return response == b'OK'
        except Exception as e:
            logging.error(f"Authentication error: {e}")
            return False

    def connect(self):
        self.save_routes()

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(10)
            logging.info(f"Connecting to {self.server_host}:{self.server_port}...")
            sock.connect((self.server_host, self.server_port))

            if not self.authenticate(sock):
                logging.error("Authentication failed")
                sock.close()
                self.restore_routes()
                return

            sock.settimeout(None)
            logging.info(f"Connected to VPN server {self.server_host}:{self.server_port}")

            self.tun = self.create_tun()
            self.running = True

            while self.running:
                readable, _, _ = select.select([sock, self.tun], [], [], 1)

                for s in readable:
                    try:
                        if s == sock:
                            data = sock.recv(4096)
                            if not data:
                                logging.warning("Server disconnected, restoring network...")
                                self.restore_routes()
                                return
                            self.tun.write(data)
                        elif s == self.tun:
                            packet = self.tun.read(4096)
                            if packet:
                                sock.send(packet)
                    except Exception as e:
                        logging.error(f"Connection lost: {e}")
                        logging.info("Restoring network...")
                        self.restore_routes()
                        return

        except KeyboardInterrupt:
            logging.info("Disconnecting...")
            self.restore_routes()
        except Exception as e:
            logging.error(f"Connection error: {e}")
            logging.info("Restoring network...")
            self.restore_routes()
        finally:
            self.running = False
            try:
                sock.close()
            except:
                pass
            try:
                if self.tun:
                    self.tun.close()
            except:
                pass
