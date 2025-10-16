# HiVPN

Simple VPN in pure Python.

## Install

```bash
git clone https://github.com/Bas3line/hivpn.git
cd hivpn
chmod +x build.sh
./build.sh
```

## Usage

**Server:**
```bash
sudo hivpn server mypassword
```

**Client:**
```bash
sudo hivpn client 1.2.3.4 mypassword
```

**Save config (optional):**
```bash
hivpn config --serverip 1.2.3.4 --password mypass
sudo hivpn client
```

## Requirements

- Linux with TUN/TAP support
- Root privileges
