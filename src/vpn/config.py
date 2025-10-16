import json
import os

class Config:
    def __init__(self, config_file: str = 'config.json'):
        self.config_file = config_file
        self.config = self.load()

    def load(self):
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r') as f:
                return json.load(f)
        return self.default_config()

    def default_config(self):
        return {
            'server': {
                'host': '0.0.0.0',
                'port': 8888,
                'password': 'changeme'
            },
            'client': {
                'server_host': '',
                'server_port': 8888,
                'password': 'changeme'
            }
        }

    def save(self):
        with open(self.config_file, 'w') as f:
            json.dump(self.config, f, indent=4)

    def get(self, key: str, default=None):
        keys = key.split('.')
        value = self.config
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k, default)
            else:
                return default
        return value

    def set(self, key: str, value):
        keys = key.split('.')
        config = self.config
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        config[keys[-1]] = value
        self.save()
