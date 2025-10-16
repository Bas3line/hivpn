import socket
import struct
import select
import logging
import os

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class VPNClient:
    def __init__(self, server_host: str, server_port: int, password: str):
        self.server_host = server_host
        self.server_port = server_port
        self.password = password
        self.running = False

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
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(10)
            logging.info(f"Connecting to {self.server_host}:{self.server_port}...")
            sock.connect((self.server_host, self.server_port))

            if not self.authenticate(sock):
                logging.error("Authentication failed")
                sock.close()
                return

            sock.settimeout(None)
            logging.info(f"Connected to VPN server {self.server_host}:{self.server_port}")

            tun = self.create_tun()
            self.running = True

            while self.running:
                readable, _, _ = select.select([sock, tun], [], [], 1)

                for s in readable:
                    try:
                        if s == sock:
                            data = sock.recv(4096)
                            if not data:
                                logging.warning("Server closed connection")
                                return
                            tun.write(data)
                        elif s == tun:
                            packet = tun.read(4096)
                            if packet:
                                sock.send(packet)
                    except Exception as e:
                        logging.error(f"Error processing packet: {e}")
                        return

        except KeyboardInterrupt:
            logging.info("Disconnecting...")
        except Exception as e:
            logging.error(f"Connection error: {e}")
        finally:
            self.running = False
            try:
                sock.close()
            except:
                pass
            try:
                tun.close()
            except:
                pass
