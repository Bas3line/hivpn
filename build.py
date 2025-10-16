import PyInstaller.__main__
import os
import sys

PyInstaller.__main__.run([
    'vpn.py',
    '--onefile',
    '--name=hivpn',
    '--clean',
    '--noconfirm',
    '--strip',
    '--noupx',
])
