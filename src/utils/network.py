"""
Network Scanning Utilities for Remote System Discovery.

This module provides comprehensive network scanning and connectivity testing
capabilities for discovering and testing remote systems. It supports ICMP ping,
TCP port scanning, service detection, OS fingerprinting, and reverse DNS lookup.

Functions:
    scan_network: Scan a network range for active hosts
    scan_host: Scan a single host for services
    ping_host_quick: Quick ICMP ping check
    check_port_quick: Quick TCP port check
    reverse_dns_lookup: Perform reverse DNS lookup
    guess_os: Guess OS based on open ports
    check_target: Perform specific health check on target
    get_service_name: Get service name for port number
    ConnectionTester: Test various remote connection methods

Usage:
    from src.utils.network import scan_network, ping_host_quick, check_port

    # Scan a network range
    results = scan_network("192.168.1.0/24", scan_types=["ping", "port"])

    # Check if host is alive
    if ping_host_quick("192.168.1.1"):
        print("Host is online")

    # Check specific port
    result = check_port_quick("192.168.1.1", 22)
    if result:
        print("SSH port is open")

Requirements:
    - Python standard library (socket, subprocess, ipaddress)
    - Optional: concurrent.futures for parallel scanning
"""

import ipaddress
import logging
import os
import socket
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

logger = logging.getLogger(__name__)


def scan_network(
    network_range: str,
    scan_types: list[str] | None = None,
    ports: list[int] | None = None,
    timeout: int = 3,
) -> dict:
    """
    Scan a network range for active hosts and services.

    Performs a comprehensive scan of the specified network range,
    checking for alive hosts and optionally scanning for open ports.

    Args:
        network_range: CIDR notation for network (e.g., "192.168.1.0/24")
        scan_types: List of scan types to perform (default: ["ping", "port"])
        ports: List of ports to scan if port scanning enabled
        timeout: Timeout in seconds for each host check

    Returns:
        dict: Scan results with network, hosts found, scan time

    Example:
        results = scan_network(
            network_range="10.0.0.0/24",
            scan_types=["ping", "port"],
            ports=[22, 80, 443, 3389],
            timeout=5
        )
        print(f"Found {len(results['hosts_found'])} active hosts")
    """
    if scan_types is None:
        scan_types = ["ping", "port"]

    if ports is None:
        ports = [22, 80, 445, 3389]

    results: dict[str, Any] = {
        "network": network_range,
        "hosts_found": [],
        "scan_time": None,
        "scan_types": scan_types,
    }

    try:
        network = ipaddress.ip_network(network_range, strict=False)
        hosts = list(network.hosts())

        logger.info(f"Scanning {len(hosts)} hosts in {network_range}")

        with ThreadPoolExecutor(max_workers=50) as executor:
            futures = {
                executor.submit(scan_host, str(host), scan_types, ports, timeout): host
                for host in hosts
            }

            for future in as_completed(futures):
                try:
                    host_result = future.result()
                    if host_result.get("alive"):
                        results["hosts_found"].append(host_result)
                except Exception as e:
                    logger.debug(f"Scan error: {e}")

        results["scan_time"] = len(results["hosts_found"])
        logger.info(f"Found {len(results['hosts_found'])} active hosts")

    except Exception as e:
        logger.error(f"Network scan failed: {e}")
        results["error"] = str(e)

    return results


def scan_host(ip: str, scan_types: list[str], ports: list[int], timeout: int) -> dict:
    """
    Scan a single host for availability and services.

    Performs ping check and optional port scanning on a single host,
    also attempting reverse DNS and OS guessing.

    Args:
        ip: IP address to scan
        scan_types: List of scan types to perform
        ports: List of ports to scan
        timeout: Timeout in seconds

    Returns:
        dict: Host scan results with alive status, ports, services, etc.
    """
    result: dict[str, Any] = {
        "ip": ip,
        "alive": False,
        "ports": [],
        "services": [],
        "hostname": None,
        "os_hint": None,
    }

    try:
        if "ping" in scan_types:
            if not ping_host_quick(ip, timeout):
                return result

        result["alive"] = True

        if "port" in scan_types:
            for port in ports:
                if check_port_quick(ip, port, timeout):
                    result["ports"].append(port)
                    result["services"].append(get_service_name(port))

        result["hostname"] = reverse_dns_lookup(ip)
        result["os_hint"] = guess_os(ip, result.get("ports", []))

    except Exception as e:
        logger.debug(f"Host scan error for {ip}: {e}")

    return result


def ping_host_quick(host: str, timeout: int = 3) -> bool:
    """
    Quick ping check using ICMP.

    Sends a single ICMP echo request to check if host is reachable.

    Args:
        host: Hostname or IP address to ping
        timeout: Timeout in seconds

    Returns:
        bool: True if host responds to ping, False otherwise
    """
    try:
        param = "-n" if os.name == "nt" else "-c"
        result = subprocess.run(
            ["ping", param, "1", "-w", str(timeout * 1000), host],
            capture_output=True,
            timeout=timeout + 1,
        )
        return result.returncode == 0
    except Exception:
        return False


def check_port_quick(host: str, port: int, timeout: int = 3) -> bool:
    """
    Quick TCP port check.

    Attempts a TCP connection to check if port is open.

    Args:
        host: Hostname or IP address
        port: Port number to check
        timeout: Timeout in seconds

    Returns:
        bool: True if port is open, False otherwise
    """
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except Exception:
        return False


def reverse_dns_lookup(ip: str) -> str | None:
    """
    Perform reverse DNS lookup.

    Attempts to resolve an IP address to a hostname.

    Args:
        ip: IP address to look up

    Returns:
        str: Hostname if found, None if lookup fails
    """
    try:
        hostname, _, _ = socket.gethostbyaddr(ip)
        return hostname
    except Exception:
        return None


def guess_os(ip: str, open_ports: list[int]) -> str:
    """
    Guess operating system based on open ports.

    Analyzes open ports to make an educated guess about the
    operating system running on the host.

    Args:
        ip: IP address of the host
        open_ports: List of open port numbers

    Returns:
        str: Guessed OS type (windows, linux, network, printer, unknown)

    Heuristics:
        - Windows: Ports 3389, 445, 139, 135
        - Linux: Ports 22, 80, 443
        - Network devices: Ports 22, 23, 80, 443, 161
        - Printers: Ports 80, 631, 9100
    """
    os_indicators = {
        "windows": [3389, 445, 139, 135],
        "linux": [22, 80, 443],
        "network": [22, 23, 80, 443, 161],
        "printer": [80, 631, 9100],
    }

    if not open_ports:
        return "unknown"

    for os_type, ports in os_indicators.items():
        matches = sum(1 for p in open_ports if p in ports)
        if matches >= len(ports) // 2 + 1:
            return os_type

    return "unknown"


def check_target(
    target: str, check_type: str, port: int | None = None, timeout: int = 10
) -> dict:
    """
    Perform specific health check on a target.

    Executes a specific type of health check on the target system.

    Args:
        target: Target hostname or IP address
        check_type: Type of check (ping, port, service, url)
        port: Port number for port/service checks
        timeout: Timeout in seconds

    Returns:
        dict: Check results with status and details

    Check Types:
        - ping: ICMP ping to check host availability
        - port: TCP connection to specific port
        - service: Check if specific service is running
        - url: HTTP/HTTPS request to check web service
    """
    result: dict[str, Any] = {"target": target, "check_type": check_type, "timestamp": None}

    import datetime

    result["timestamp"] = datetime.datetime.now(datetime.timezone.utc).isoformat()

    if check_type == "ping":
        if ping_host_quick(target, timeout):
            result["status"] = "online"
        else:
            result["status"] = "offline"

    elif check_type == "port":
        if port is None:
            port = 80
        if check_port_quick(target, port, timeout):
            result["status"] = "open"
            result["port"] = port
            result["service"] = get_service_name(port)
        else:
            result["status"] = "closed"
            result["port"] = port

    elif check_type == "service":
        if port and check_port_quick(target, port, timeout):
            result["status"] = "running"
            result["port"] = port
            result["service"] = get_service_name(port)
        else:
            result["status"] = "not running"

    elif check_type == "url":
        try:
            import urllib.request

            response = urllib.request.urlopen(f"http://{target}", timeout=timeout)
            result["status"] = "accessible"
            result["code"] = response.getcode()
        except Exception as e:
            result["status"] = "error"
            result["error"] = str(e)

    return result


def get_service_name(port: int) -> str:
    """
    Get common service name for a port number.

    Maps well-known port numbers to their standard service names.

    Args:
        port: Port number

    Returns:
        str: Service name or "Unknown" if not in known list

    Known Ports:
        21=FTP, 22=SSH, 23=Telnet, 25=SMTP, 53=DNS, 80=HTTP,
        110=POP3, 143=IMAP, 443=HTTPS, 445=SMB, 993=IMAPS,
        995=POP3S, 1433=MSSQL, 1521=Oracle, 3306=MySQL,
        3389=RDP, 5432=PostgreSQL, 5900=VNC, 5985=WinRM,
        5986=WinRM-SSL, 6379=Redis, 8080=HTTP-Proxy,
        8443=HTTPS-Alt, 27017=MongoDB
    """
    services = {
        21: "FTP",
        22: "SSH",
        23: "Telnet",
        25: "SMTP",
        53: "DNS",
        80: "HTTP",
        110: "POP3",
        143: "IMAP",
        443: "HTTPS",
        445: "SMB",
        993: "IMAPS",
        995: "POP3S",
        1433: "MSSQL",
        1521: "Oracle",
        3306: "MySQL",
        3389: "RDP",
        5432: "PostgreSQL",
        5900: "VNC",
        5985: "WinRM",
        5986: "WinRM-SSL",
        6379: "Redis",
        8080: "HTTP-Proxy",
        8443: "HTTPS-Alt",
        27017: "MongoDB",
    }
    return services.get(port, "Unknown")


class ConnectionTester:
    """
    Test various remote connection methods.

    Provides methods to test connectivity for common remote access
    protocols including SSH, RDP, VNC, WinRM, and SMB.

    Attributes:
        host: Target hostname or IP address
        timeout: Connection timeout in seconds
        results: Last test results

    Usage:
        tester = ConnectionTester("192.168.1.100", timeout=10)

        # Test SSH
        result = tester.test_ssh()
        print(result.status)

        # Test all common ports
        results = tester.test_all_common()
    """

    def __init__(self, host: str, timeout: int = 10):
        self.host = host
        self.timeout = timeout
        self.results: dict[str, Any] = {}

    def test_ssh(self, port: int = 22) -> dict:
        return self._test_port(port, "SSH")

    def test_rdp(self, port: int = 3389) -> dict:
        return self._test_port(port, "RDP")

    def test_smb(self, port: int = 445) -> dict:
        return self._test_port(port, "SMB")

    def test_winrm(self, port: int = 5985) -> dict:
        return self._test_port(port, "WinRM")

    def test_vnc(self, port: int = 5900) -> dict:
        return self._test_port(port, "VNC")

    def _test_port(self, port: int, service: str) -> dict:
        """
        Generic port test for a service.

        Performs TCP connection test on specified port.

        Args:
            port: Port number to test
            service: Service name for logging

        Returns:
            dict: Test result with host, port, service, and status
        """
        result = {
            "host": self.host,
            "port": port,
            "service": service,
            "status": "unknown",
        }

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.timeout)
            conn_result = sock.connect_ex((self.host, port))
            sock.close()

            result["status"] = "open" if conn_result == 0 else "closed"

        except Exception as e:
            result["status"] = "error"
            result["error"] = str(e)

        return result

    def test_all_common(self) -> list[dict]:
        """
        Test all common remote access ports.

        Performs connectivity tests on all commonly used remote
        access protocol ports in sequence.

        Returns:
            list: List of test results for each service

        Ports Tested:
            22 (SSH), 23 (Telnet), 3389 (RDP), 445 (SMB),
            5900 (VNC), 5985 (WinRM)
        """
        tests = [
            (22, "SSH"),
            (23, "Telnet"),
            (3389, "RDP"),
            (445, "SMB"),
            (5900, "VNC"),
            (5985, "WinRM"),
        ]

        results = []
        for port, service in tests:
            results.append(self._test_port(port, service))

        self.results = results  # type: ignore[assignment]
        return results
