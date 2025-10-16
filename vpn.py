#!/usr/bin/env python3

import sys
import argparse
import os
from src.vpn.server import VPNServer
from src.vpn.client import VPNClient
from src.vpn.config import Config

BANNER = """
  _   _ _____     ______  _   _
 | | | |_   _|   / /  _ \| \ | |
 | |_| | | |    / /| |_) |  \| |
 |  _  | | |   / / |  __/| . ` |
 | | | |_| |_ / /  | |   | |\  |
 |_| |_|_____/_/   |_|   |_| \_|
"""

def print_banner():
    print("\033[96m" + BANNER + "\033[0m")

def main():
    if len(sys.argv) == 1:
        print_banner()
        print("Usage:")
        print("  \033[92mhivpn server <password>\033[0m          Start VPN server")
        print("  \033[92mhivpn client <ip> <password>\033[0m    Connect to VPN")
        print("  \033[93mhivpn config --serverip <ip>\033[0m    Save server IP")
        print()
        sys.exit(0)

    parser = argparse.ArgumentParser(description='HiVPN - Simple Python VPN', add_help=False)
    subparsers = parser.add_subparsers(dest='command', help='Commands')

    server_parser = subparsers.add_parser('server', help='Run VPN server', add_help=False)
    server_parser.add_argument('password', nargs='?', help='Server password')
    server_parser.add_argument('--port', type=int, default=8888, help='Server port')

    client_parser = subparsers.add_parser('client', help='Connect to VPN server', add_help=False)
    client_parser.add_argument('server_ip', nargs='?', help='Server IP address')
    client_parser.add_argument('password', nargs='?', help='Server password')
    client_parser.add_argument('--port', type=int, default=8888, help='Server port')

    config_parser = subparsers.add_parser('config', help='Configure VPN', add_help=False)
    config_parser.add_argument('--serverip', type=str, help='Set server IP')
    config_parser.add_argument('--password', type=str, help='Set password')
    config_parser.add_argument('--port', type=int, help='Set port')

    args = parser.parse_args()

    config_file = os.path.expanduser('~/.hivpn.conf')
    config = Config(config_file)

    if args.command == 'config':
        if args.serverip:
            config.set('client.server_host', args.serverip)
            print(f"✓ Server IP: {args.serverip}")
        if args.password:
            config.set('client.password', args.password)
            print(f"✓ Password saved")
        if args.port:
            config.set('client.server_port', args.port)
            print(f"✓ Port: {args.port}")
        sys.exit(0)

    elif args.command == 'server':
        if not args.password:
            print("Error: Password required")
            print("Usage: hivpn server <password>")
            sys.exit(1)

        print_banner()
        print(f"Starting server on port {args.port}...")
        server = VPNServer('0.0.0.0', args.port, args.password)
        server.start()

    elif args.command == 'client':
        server_host = args.server_ip or config.get('client.server_host')
        if not server_host:
            print("Error: Server IP required")
            print("Usage: hivpn client <server_ip> <password>")
            print("   or: hivpn config --serverip <ip> && hivpn client")
            sys.exit(1)

        password = args.password or config.get('client.password')
        if not password:
            print("Error: Password required")
            sys.exit(1)

        print_banner()
        print(f"Connecting to {server_host}:{args.port}...")
        client = VPNClient(server_host, args.port, password)
        client.connect()

if __name__ == '__main__':
    main()

