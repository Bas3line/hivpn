import socket
import subprocess
import urllib.request
import logging

def get_public_ip():
    methods = [
        lambda: urllib.request.urlopen('https://api.ipify.org', timeout=3).read().decode('utf-8').strip(),
        lambda: urllib.request.urlopen('https://ifconfig.me', timeout=3).read().decode('utf-8').strip(),
        lambda: urllib.request.urlopen('https://icanhazip.com', timeout=3).read().decode('utf-8').strip(),
        lambda: socket.gethostbyname(socket.gethostname())
    ]

    for method in methods:
        try:
            ip = method()
            if ip and ip != '127.0.0.1':
                return ip
        except:
            continue

    return None

def get_default_interface():
    try:
        result = subprocess.run('ip route | grep default', shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            parts = result.stdout.split()
            if len(parts) >= 5:
                return parts[4]
    except:
        pass
    return 'eth0'

def check_port_available(port):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(('0.0.0.0', port))
        sock.close()
        return True
    except:
        return False
