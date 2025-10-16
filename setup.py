#!/usr/bin/env python3

import subprocess
import sys
import os
import secrets
import string
from src.vpn.utils import get_public_ip

def run(cmd, check=True):
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if check and result.returncode != 0:
            print(f"Error: {result.stderr}")
            return False
        return True
    except Exception as e:
        print(f"Error: {e}")
        return False

def check_root():
    if os.geteuid() != 0:
        print("Run as root: sudo python3 setup.py")
        sys.exit(1)

def check_tun():
    if not os.path.exists('/dev/net/tun'):
        print("TUN device not found. Creating...")
        run('mkdir -p /dev/net')
        run('mknod /dev/net/tun c 10 200')
        run('chmod 666 /dev/net/tun')

def install_deps():
    print("Installing dependencies...")
    run('apt update', check=False)
    run('apt install -y python3 iptables iproute2', check=False)

def generate_password():
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(16))

def setup_server():
    print("\n=== SERVER SETUP ===\n")

    check_root()
    check_tun()
    install_deps()

    password = generate_password()
    public_ip = get_public_ip()

    if not public_ip:
        print("Warning: Could not detect public IP")
        public_ip = input("Enter your server public IP: ").strip()

    config = {
        "server": {
            "host": "0.0.0.0",
            "port": 8888,
            "password": password
        }
    }

    import json
    with open('config.json', 'w') as f:
        json.dump(config, f, indent=4)

    run('chmod 600 config.json')

    print("Opening firewall port 8888...")
    run('ufw allow 8888/tcp', check=False)
    run('iptables -I INPUT -p tcp --dport 8888 -j ACCEPT', check=False)

    print("\n" + "="*50)
    print("SERVER SETUP COMPLETE")
    print("="*50)
    print(f"\nServer IP: {public_ip}")
    print(f"Password: {password}")
    print(f"\nStart server: sudo ./vpn server")
    print(f"\nGive this to your client:")
    print(f"  sudo ./vpn client {public_ip} {password}")
    print("="*50 + "\n")

def setup_client(server_ip, password):
    print("\n=== CLIENT SETUP ===\n")

    check_root()
    check_tun()
    install_deps()

    config = {
        "client": {
            "server_host": server_ip,
            "server_port": 8888,
            "password": password
        }
    }

    import json
    with open('config.json', 'w') as f:
        json.dump(config, f, indent=4)

    run('chmod 600 config.json')

    print("\n" + "="*50)
    print("CLIENT SETUP COMPLETE")
    print("="*50)
    print(f"\nServer: {server_ip}")
    print(f"\nConnect: sudo ./vpn client")
    print("="*50 + "\n")

def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  sudo python3 setup.py server")
        print("  sudo python3 setup.py client <server_ip> <password>")
        sys.exit(1)

    mode = sys.argv[1]

    if mode == 'server':
        setup_server()
    elif mode == 'client':
        if len(sys.argv) != 4:
            print("Usage: sudo python3 setup.py client <server_ip> <password>")
            sys.exit(1)
        setup_client(sys.argv[2], sys.argv[3])
    else:
        print("Invalid mode. Use 'server' or 'client'")
        sys.exit(1)

if __name__ == '__main__':
    main()
