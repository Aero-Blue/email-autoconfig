from typing import List
import requests
import untangle
from urllib.parse import urlsplit


class ServerConfig:
    __slots__ = ['protocol', 'hostname', 'port', 'socket_type', 'authentication', 'username']

    def __init__(self, protocol: str, hostname: str, port: int, socket_type: str, authentication: str, username: str):
        self.protocol = protocol
        self.hostname = hostname
        self.port = port
        self.socket_type = socket_type
        self.authentication = authentication
        self.username = username

    def __str__(self):
        return f"{self.hostname}:{self.port}"

    def __repr__(self):
        args = ', '.join([f"{slot}='{getattr(self, slot)}'" for slot in self.__slots__])
        return f"{self.__class__.__name__}({args})"


class ClientConfig:
    __slots__ = ['domain', 'xml', 'emailProvider', 'configs']
    VERSION = 1.1
    DATABASE_URL = f"https://autoconfig.thunderbird.net/v{VERSION}"

    def __init__(self, domain: str):
        """Take a domain, find all associated mail configurations for it"""
        self.domain = self.fix_url(domain)
        self.xml = self.request_config()
        if not self.xml:
            raise Exception(f"No configuration file found for '{domain}'")
        self.emailProvider = None
        self.configs = self.parse_config()

    @classmethod
    def fix_url(cls, domain):
        """Add http:// or https:// to domain if not present, so it can be properly parsed"""
        if not (domain.startswith("http://") or domain.startswith("https://")):
            domain = "http://" + domain
        return urlsplit(domain).netloc

    def request_config(self):
        """Request xml file, if request is invalid, return None"""
        config_url = "/".join((self.DATABASE_URL, self.domain))
        with requests.get(config_url) as response:
            text = response.text if response.ok else None
        return text

    def parse_config(self) -> List[ServerConfig]:
        """Parse servers found in config into ServerConfig objects"""
        xml = untangle.parse(self.xml)
        root = xml.clientConfig.emailProvider
        self.emailProvider = xml.clientConfig.emailProvider["id"]
        servers = []
        for _config in root.incomingServer, root.outgoingServer:
            for attr in _config:
                protocol, hostname, port = attr["type"], attr.hostname.cdata, int(attr.port.cdata)
                socket_type, authentication = attr.socketType.cdata, attr.authentication.cdata
                username = attr.username.cdata
                server = ServerConfig(protocol, hostname, port, socket_type, authentication, username)
                servers.append(server)
        return servers

    def _get_config(self, protocol: str) -> ServerConfig:
        """Search for a config by its protocol, return None if not found"""
        for _config in self.configs:
            if _config.protocol == protocol.lower():
                return _config

    @classmethod
    def get_config(cls, domain: str, protocol: str):
        """Take in domain and protocol, return specific configuration, if found"""
        return cls(domain)._get_config(protocol)

    def get_protocol(self, protocol: str):
        return self._get_config(protocol)

    @classmethod
    def get_configs(cls, domain: str):
        """Take domain, return all associated configs"""
        return cls(domain)._get_configs()

    def _get_configs(self):
        """Private method, return configs, empty if None"""
        return self.configs
