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

            result = subprocess.run('ip route show default', shell=True, capture_output=True, text=True)
            self.original_default = result.stdout.strip()

            try:
                with open('/etc/resolv.conf', 'r') as f:
                    self.original_dns = f.read()
            except:
                self.original_dns = None

            logging.info("Saved original routes and DNS")
        except Exception as e:
            logging.error(f"Error saving routes: {e}")

    def restore_routes(self):
        try:
            os.system('ip route del default via 10.8.0.1 dev tun0 2>/dev/null')

            if self.tun:
                os.system('ip link set tun0 down 2>/dev/null')
                os.system('ip link delete tun0 2>/dev/null')

            if hasattr(self, 'original_default') and self.original_default:
                os.system('ip route del default 2>/dev/null')
                os.system(f'ip route add {self.original_default}')

            if hasattr(self, 'original_dns') and self.original_dns:
                try:
                    with open('/etc/resolv.conf', 'w') as f:
                        f.write(self.original_dns)
                except:
                    pass

            os.system('ip route flush cache')
            logging.info("Network routes and DNS restored")
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

            result = subprocess.run('ip route show default', shell=True, capture_output=True, text=True)
            default_route = result.stdout.strip()
            if default_route:
                parts = default_route.split()
                if 'via' in parts:
                    gw_idx = parts.index('via') + 1
                    original_gw = parts[gw_idx]
                    dev_idx = parts.index('dev') + 1 if 'dev' in parts else -1
                    original_dev = parts[dev_idx] if dev_idx > 0 else None

                    if original_dev:
                        os.system(f'ip route add {self.server_host}/32 via {original_gw} dev {original_dev}')

            os.system('ip route del default 2>/dev/null')
            os.system(f'ip route add default via 10.8.0.1 dev {name}')

            try:
                with open('/etc/resolv.conf', 'w') as f:
                    f.write('nameserver 8.8.8.8\nnameserver 1.1.1.1\n')
                logging.info("DNS configured to use 8.8.8.8 and 1.1.1.1")
            except Exception as e:
                logging.warning(f"Could not update DNS: {e}")

            logging.info(f"TUN interface {name} created with IP 10.8.0.2/24 - All traffic routed through VPN")
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
            print("\n\nDisconnecting from VPN...")
            self.restore_routes()
            print("Network restored. Goodbye!")
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
