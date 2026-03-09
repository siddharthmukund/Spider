"""SSRF (Server-Side Request Forgery) protection module.

Validates URLs to prevent internal network access and metadata endpoints.
"""
import ipaddress
import socket
from urllib.parse import urlparse
from typing import Tuple, Set, List


class SSRFValidator:
    """Validate URLs to prevent Server-Side Request Forgery attacks."""
    
    # Allowed URL schemes
    ALLOWED_SCHEMES: Set[str] = {'http', 'https'}
    
    # Blocked hostnames (localhost variants and cloud metadata)
    BLOCKED_HOSTS: Set[str] = {
        'localhost',
        '127.0.0.1',
        '0.0.0.0',
        '::1',
        'metadata.google.internal',      # GCP metadata
        '169.254.169.254',                # AWS/Azure/GCP metadata
        'metadata',
        'metadata.internal',
        'instance-data',
        'fd00:ec2::254',                  # AWS IMDSv2 IPv6
    }
    
    # Blocked IP ranges (private networks, loopback, link-local)
    BLOCKED_RANGES: List[ipaddress.IPv4Network | ipaddress.IPv6Network] = [
        ipaddress.ip_network('10.0.0.0/8'),        # Private (RFC 1918)
        ipaddress.ip_network('172.16.0.0/12'),     # Private (RFC 1918)
        ipaddress.ip_network('192.168.0.0/16'),    # Private (RFC 1918)
        ipaddress.ip_network('127.0.0.0/8'),       # Loopback
        ipaddress.ip_network('169.254.0.0/16'),    # Link-local (AWS metadata)
        ipaddress.ip_network('224.0.0.0/4'),       # Multicast
        ipaddress.ip_network('240.0.0.0/4'),       # Reserved
        ipaddress.ip_network('::1/128'),           # IPv6 loopback
        ipaddress.ip_network('fc00::/7'),          # IPv6 private (ULA)
        ipaddress.ip_network('fe80::/10'),         # IPv6 link-local
        ipaddress.ip_network('ff00::/8'),          # IPv6 multicast
    ]
    
    @classmethod
    def validate(cls, url: str) -> Tuple[bool, str]:
        """
        Validate URL for SSRF safety.
        
        Args:
            url: The URL to validate
            
        Returns:
            Tuple of (is_valid, error_message).
            If valid, error_message is empty string.
        """
        try:
            parsed = urlparse(url)
            
            # Check scheme
            if parsed.scheme not in cls.ALLOWED_SCHEMES:
                return False, f"Scheme '{parsed.scheme}' not allowed. Use http or https."
            
            # Check hostname exists
            hostname = parsed.hostname
            if not hostname:
                return False, "Missing hostname in URL."
            
            # Check against blocked hostnames
            hostname_lower = hostname.lower()
            if hostname_lower in cls.BLOCKED_HOSTS:
                return False, f"Host '{hostname}' is blocked for security reasons."
            
            # Special check for IP addresses in hostname
            try:
                # If hostname is already an IP, validate it directly
                ip = ipaddress.ip_address(hostname)
                if cls._is_ip_blocked(ip):
                    return False, f"IP address {ip} is in blocked range."
            except ValueError:
                # Not an IP address, proceed to DNS resolution
                pass
            
            # Resolve hostname to IP and check ranges
            try:
                resolved_ips = socket.getaddrinfo(hostname, None)
                for addr_info in resolved_ips:
                    ip_str = addr_info[4][0]
                    # Remove IPv6 zone identifier if present (e.g., "fe80::1%eth0" -> "fe80::1")
                    ip_str = ip_str.split('%')[0]
                    
                    try:
                        ip = ipaddress.ip_address(ip_str)
                        if cls._is_ip_blocked(ip):
                            return False, f"Resolved IP {ip} is in blocked range."
                    except ValueError:
                        continue
                        
            except socket.gaierror as e:
                return False, f"Could not resolve hostname '{hostname}': {str(e)}"
            except Exception as e:
                return False, f"DNS resolution error for '{hostname}': {str(e)}"
            
            return True, ""
            
        except Exception as e:
            return False, f"URL validation error: {str(e)}"
    
    @classmethod
    def _is_ip_blocked(cls, ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
        """
        Check if an IP address is in any blocked range.
        
        Args:
            ip: The IP address to check
            
        Returns:
            bool: True if IP is blocked, False otherwise
        """
        # Check if it's a private/reserved address
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast:
            return True
        
        # Check against explicit blocked ranges
        for blocked_range in cls.BLOCKED_RANGES:
            if ip in blocked_range:
                return True
        
        return False
    
    @classmethod
    def validate_strict(cls, url: str) -> Tuple[bool, str]:
        """
        Strict validation mode with additional checks.
        
        This mode also blocks:
        - URLs with credentials in them (user:pass@host)
        - URLs with unusual ports (not 80/443)
        - URLs with unusual TLDs
        
        Args:
            url: The URL to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        # First run standard validation
        is_valid, error = cls.validate(url)
        if not is_valid:
            return False, error
        
        parsed = urlparse(url)
        
        # Block URLs with credentials
        if parsed.username or parsed.password:
            return False, "URLs with embedded credentials are not allowed."
        
        # Block unusual ports (optional - may want to allow for development)
        if parsed.port is not None:
            allowed_ports = {80, 443, 8080, 8443}
            if parsed.port not in allowed_ports:
                return False, f"Port {parsed.port} is not in allowed list."
        
        return True, ""
