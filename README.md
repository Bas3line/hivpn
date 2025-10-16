# HiVPN

Simple VPN in pure Python.

## Install

```bash
git clone https://github.com/Bas3line/hivpn.git
cd hivpn
chmod +x build.sh
./build.sh
```

## Server Setup

**Install dependencies:**
```bash
sudo apt update
sudo apt install python3 iptables iproute2
```

**Open firewall:**
```bash
sudo ufw allow 8888/tcp
sudo ufw enable
```

**Run server (foreground):**
```bash
sudo hivpn server mypassword
```

**Run server (background service):**
```bash
sudo systemctl start hivpn@mypassword
sudo systemctl enable hivpn@mypassword
```

**View logs:**
```bash
sudo journalctl -u hivpn@mypassword -f
```

**Stop service:**
```bash
sudo systemctl stop hivpn@mypassword
```

## Client Setup

**Load TUN kernel module (required):**
```bash
sudo modprobe tun
```

If you get "Module tun not found", reinstall kernel modules and **reboot**:
```bash
# Arch Linux
sudo pacman -S linux
sudo reboot

# Debian/Ubuntu
sudo apt install --reinstall linux-modules-$(uname -r)
sudo reboot
```

To load automatically on boot:
```bash
echo "tun" | sudo tee /etc/modules-load.d/tun.conf
```

**Connect:**
```bash
sudo hivpn client 1.2.3.4 mypassword
```

**Save config:**
```bash
hivpn config --serverip 1.2.3.4 --password mypass
sudo hivpn client
```

Network auto-restores when server disconnects.

## Requirements

- Linux with TUN/TAP support
- Root privileges
