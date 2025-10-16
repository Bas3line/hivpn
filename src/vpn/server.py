import socket
import struct
import threading
import select
import logging
import os
from typing import Dict, Tuple

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class VPNServer:
    def __init__(self, host: str = '0.0.0.0', port: int = 8888, password: str = 'changeme'):
        self.host = host
        self.port = port
        self.password = password
        self.clients: Dict[str, socket.socket] = {}
        self.running = False
        self.tun = None
        self.lock = threading.Lock()

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
            os.system(f'ip addr add 10.8.0.1/24 dev {name}')
            os.system(f'ip link set {name} up')
            os.system('sysctl -w net.ipv4.ip_forward=1 >/dev/null 2>&1')

            interface = os.popen('ip route | grep default').read().split()[4]
            os.system(f'iptables -t nat -C POSTROUTING -o {interface} -j MASQUERADE 2>/dev/null || iptables -t nat -A POSTROUTING -o {interface} -j MASQUERADE')
            os.system(f'iptables -C FORWARD -i {name} -j ACCEPT 2>/dev/null || iptables -A FORWARD -i {name} -j ACCEPT')
            os.system(f'iptables -C FORWARD -o {name} -m state --state RELATED,ESTABLISHED -j ACCEPT 2>/dev/null || iptables -A FORWARD -o {name} -m state --state RELATED,ESTABLISHED -j ACCEPT')
            os.system(f'iptables -C INPUT -i {name} -j ACCEPT 2>/dev/null || iptables -A INPUT -i {name} -j ACCEPT')
            os.system(f'iptables -C OUTPUT -o {name} -j ACCEPT 2>/dev/null || iptables -A OUTPUT -o {name} -j ACCEPT')

            logging.info(f"TUN interface {name} created with IP 10.8.0.1/24")
            return tun
        except Exception as e:
            logging.error(f"Failed to create TUN interface: {e}")
            raise

    def authenticate(self, client_sock: socket.socket) -> bool:
        try:
            client_sock.settimeout(10)
            data = client_sock.recv(1024)
            if data.decode().strip() == self.password:
                client_sock.send(b'OK')
                return True
            else:
                client_sock.send(b'FAIL')
                return False
        except:
            return False

    def handle_client(self, client_sock: socket.socket, address: Tuple[str, int]):
        client_id = f"{address[0]}:{address[1]}"
        logging.info(f"Client connected: {client_id}")

        if not self.authenticate(client_sock):
            logging.warning(f"Authentication failed for {client_id}")
            client_sock.close()
            return

        with self.lock:
            self.clients[client_id] = client_sock

        logging.info(f"Client authenticated: {client_id}")
        client_sock.settimeout(None)

        try:
            while self.running:
                readable, _, _ = select.select([client_sock], [], [], 1)

                if readable:
                    try:
                        data = client_sock.recv(4096)
                        if not data:
                            break
                        self.tun.write(data)
                    except Exception as e:
                        logging.error(f"Error receiving from client {client_id}: {e}")
                        break
        except Exception as e:
            logging.error(f"Error handling client {client_id}: {e}")
        finally:
            with self.lock:
                if client_id in self.clients:
                    del self.clients[client_id]
            try:
                client_sock.close()
            except:
                pass
            logging.info(f"Client disconnected: {client_id}")

    def broadcast_tun_packets(self):
        while self.running:
            try:
                readable, _, _ = select.select([self.tun], [], [], 1)
                if readable:
                    packet = self.tun.read(4096)
                    if packet:
                        with self.lock:
                            dead_clients = []
                            for client_id, client_sock in list(self.clients.items()):
                                try:
                                    client_sock.send(packet)
                                except Exception as e:
                                    logging.error(f"Error sending to {client_id}: {e}")
                                    dead_clients.append(client_id)

                            for client_id in dead_clients:
                                if client_id in self.clients:
                                    try:
                                        self.clients[client_id].close()
                                    except:
                                        pass
                                    del self.clients[client_id]
            except Exception as e:
                logging.error(f"Error broadcasting packets: {e}")

    def start(self):
        self.tun = self.create_tun()
        server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_sock.bind((self.host, self.port))
        server_sock.listen(5)

        self.running = True
        logging.info(f"VPN Server listening on {self.host}:{self.port}")

        broadcast_thread = threading.Thread(target=self.broadcast_tun_packets)
        broadcast_thread.daemon = True
        broadcast_thread.start()

        try:
            while self.running:
                try:
                    server_sock.settimeout(1)
                    client_sock, address = server_sock.accept()
                    thread = threading.Thread(target=self.handle_client, args=(client_sock, address))
                    thread.daemon = True
                    thread.start()
                except socket.timeout:
                    continue
        except KeyboardInterrupt:
            print("\n\nShutting down VPN server...")
            logging.info("Server stopped")
        finally:
            self.running = False
            with self.lock:
                for client_sock in self.clients.values():
                    try:
                        client_sock.close()
                    except:
                        pass
            server_sock.close()
            self.tun.close()
