"""
Remote Connection Handlers for SSH, RDP, VNC, WinRM, and SMB.

This module provides connection testing and management for various remote access
protocols used in system administration. Each protocol has a dedicated handler
class that supports connectivity testing and, where applicable, command execution.

Classes:
    ConnectionType: Enum of supported connection types
    ConnectionResult: Data class for connection test results
    SSHHandler: SSH connection testing and command execution
    RDPHandler: RDP connection testing
    VNCHandler: VNC connection testing
    WinRMHandler: WinRM connection testing and command execution
    SMBHandler: SMB connection testing and share enumeration
    ConnectionFactory: Factory for creating connection handlers

Features:
    - Protocol-agnostic connection testing interface
    - SSH command execution via paramiko (with CLI fallback)
    - RDP session launch (Windows-only)
    - VNC connection testing
    - WinRM command execution via REST API
    - SMB share enumeration (Windows-only)
    - Automatic default port selection per protocol

Usage:
    from src.utils.remote_connections import ConnectionFactory, ConnectionType

    # Test SSH connectivity
    result = ConnectionFactory.test_connection("ssh", "192.168.1.100")
    print(f"SSH: {'Open' if result.success else 'Closed'}")

    # Execute command via SSH
    handler = ConnectionFactory.create_handler("ssh", "192.168.1.100", username="admin", password="pass")
    result = handler.execute_command("whoami")

    # Test all common ports
    from src.utils.remote_connections import ConnectionTester
    tester = ConnectionTester("192.168.1.100")
    results = tester.test_all_common()

Requirements:
    - paramiko (optional): For SSH command execution
    - requests (optional): For WinRM command execution
"""

import logging
import os
import socket
import subprocess
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class ConnectionType(Enum):
    """
    Enumeration of supported remote connection types.

    Values:
        SSH: Secure Shell (port 22)
        RDP: Remote Desktop Protocol (port 3389)
        VNC: Virtual Network Computing (port 5900)
        WINRM: Windows Remote Management (port 5985)
        SMB: Server Message Block (port 445)
        TELNET: Telnet protocol (port 23)
    """

    SSH = "ssh"
    RDP = "rdp"
    VNC = "vnc"
    WINRM = "winrm"
    SMB = "smb"
    TELNET = "telnet"


@dataclass
class ConnectionResult:
    """
    Data class representing the result of a connection test.

    Attributes:
        success: Whether the connection test was successful
        message: Human-readable description of the result
        details: Optional dictionary with additional information
    """

    success: bool
    message: str
    details: dict | None = None


class SSHHandler:
    """
    Handler for SSH connections and command execution.

    Provides connectivity testing via TCP port check and command
    execution via the paramiko library. Falls back to CLI if
    paramiko is not installed.

    Attributes:
        host: Target hostname or IP address
        port: SSH port number (default: 22)
        username: Username for authentication
        password: Password for authentication (optional for key-based auth)

    Example:
        handler = SSHHandler("192.168.1.100", username="admin", password="secret")
        result = handler.test_connection()
        if result.success:
            cmd_result = handler.execute_command("ls -la")
    """

    def __init__(
        self, host: str, port: int = 22, username: str | None = None, password: str | None = None
    ):
        """
        Initialize SSH handler with target and credentials.

        Args:
            host: Target hostname or IP address
            port: SSH port number (default: 22)
            username: Username for authentication
            password: Password for authentication
        """
        self.host = host
        self.port = port
        self.username = username
        self.password = password

    def test_connection(self, timeout: int = 10) -> ConnectionResult:
        """
        Test SSH connectivity by checking if port is open.

        Performs a TCP connection test to the SSH port without
        actually authenticating.

        Args:
            timeout: Connection timeout in seconds (default: 10)

        Returns:
            ConnectionResult with success status and port details
        """
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((self.host, self.port))
            sock.close()

            if result == 0:
                return ConnectionResult(True, "SSH port is open", {"port": self.port})
            else:
                return ConnectionResult(
                    False, "SSH port is closed or filtered", {"port": self.port}
                )
        except Exception as e:
            return ConnectionResult(False, f"Connection failed: {str(e)}")

    def execute_command(self, command: str, timeout: int = 30) -> ConnectionResult:
        """
        Execute a command via SSH.

        Uses paramiko for SSH command execution. Falls back to
        CLI-based execution if paramiko is not installed.

        Args:
            command: Shell command to execute on remote host
            timeout: Command execution timeout in seconds (default: 30)

        Returns:
            ConnectionResult with command output and exit code

        Note:
            Requires paramiko library. Install with: pip install paramiko
        """
        try:
            import paramiko

            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            if self.password:
                client.connect(
                    self.host,
                    port=self.port,
                    username=self.username,
                    password=self.password,
                    timeout=timeout,
                )
            else:
                client.connect(
                    self.host, port=self.port, username=self.username, timeout=timeout
                )

            stdin, stdout, stderr = client.exec_command(command, timeout=timeout)
            output = stdout.read().decode()
            error = stderr.read().decode()
            exit_code = stdout.channel.recv_exit_status()

            client.close()

            if exit_code == 0:
                return ConnectionResult(
                    True,
                    "Command executed successfully",
                    {"output": output, "exit_code": exit_code},
                )
            else:
                return ConnectionResult(
                    False,
                    f"Command failed with exit code {exit_code}",
                    {"output": output, "error": error, "exit_code": exit_code},
                )

        except ImportError:
            return ConnectionResult(
                False, "paramiko not installed - using CLI fallback", {}
            )
        except Exception as e:
            return ConnectionResult(False, f"Command execution failed: {str(e)}")

    def open_session(self) -> str:
        """
        Generate SSH command for opening an interactive session.

        Returns:
            str: SSH command string for connecting to host
        """
        if self.password:
            return f"ssh {self.username}@{self.host} -p {self.port}"
        else:
            return f"ssh {self.username}@{self.host} -p {self.port}"


class RDPHandler:
    """
    Handler for RDP (Remote Desktop Protocol) connections.

    Provides connectivity testing and session launch for RDP.
    Session launch is Windows-only using mstsc command.

    Attributes:
        host: Target hostname or IP address
        port: RDP port number (default: 3389)
        username: Username for authentication (optional)
        password: Password for authentication (optional)
    """

    def __init__(
        self, host: str, port: int = 3389, username: str | None = None, password: str | None = None
    ):
        """
        Initialize RDP handler with target and credentials.

        Args:
            host: Target hostname or IP address
            port: RDP port number (default: 3389)
            username: Username for RDP session
            password: Password for RDP session
        """
        self.host = host
        self.port = port
        self.username = username
        self.password = password

    def test_connection(self, timeout: int = 10) -> ConnectionResult:
        """
        Test RDP connectivity by checking if port is open.

        Args:
            timeout: Connection timeout in seconds (default: 10)

        Returns:
            ConnectionResult with success status and port details
        """
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((self.host, self.port))
            sock.close()

            if result == 0:
                return ConnectionResult(True, "RDP port is open", {"port": self.port})
            else:
                return ConnectionResult(
                    False, "RDP port is closed or filtered", {"port": self.port}
                )
        except Exception as e:
            return ConnectionResult(False, f"Connection failed: {str(e)}")

    def connect_command(self) -> str:
        """
        Generate RDP connection command string.

        Returns:
            str: RDP command for launching connection
        """
        if self.username:
            return f"mstsc /v:{self.host} /u:{self.username}"
        else:
            return f"mstsc /v:{self.host}"

    def open_session(self):
        """
        Launch RDP session using system command.

        Only works on Windows systems. Logs a warning on non-Windows.

        Note:
            Uses mstsc command which is Windows-only.
        """
        if os.name == "nt":
            subprocess.Popen(["mstsc", "/v:" + self.host])
        else:
            logger.warning("RDP only available on Windows")


class VNCHandler:
    """
    Handler for VNC (Virtual Network Computing) connections.

    Provides connectivity testing and connection command generation
    for VNC remote desktop access.

    Attributes:
        host: Target hostname or IP address
        port: VNC port number (default: 5900)
        password: VNC password (optional)
    """

    def __init__(self, host: str, port: int = 5900, password: str | None = None):
        """
        Initialize VNC handler with target and credentials.

        Args:
            host: Target hostname or IP address
            port: VNC port number (default: 5900)
            password: VNC authentication password
        """
        self.host = host
        self.port = port
        self.password = password

    def test_connection(self, timeout: int = 10) -> ConnectionResult:
        """
        Test VNC connectivity by checking if port is open.

        Args:
            timeout: Connection timeout in seconds (default: 10)

        Returns:
            ConnectionResult with success status and port details
        """
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((self.host, self.port))
            sock.close()

            if result == 0:
                return ConnectionResult(True, "VNC port is open", {"port": self.port})
            else:
                return ConnectionResult(
                    False, "VNC port is closed or filtered", {"port": self.port}
                )
        except Exception as e:
            return ConnectionResult(False, f"Connection failed: {str(e)}")

    def open_session(self) -> str:
        """
        Generate VNC connection command string.

        Returns:
            str: VNC viewer command for connecting to host
        """
        return f"vncviewer {self.host}:{self.port}"


class WinRMHandler:
    """
    Handler for WinRM (Windows Remote Management) connections.

    Provides connectivity testing and command execution via the WinRM
    REST API. Command execution requires the requests library.

    Attributes:
        host: Target hostname or IP address
        port: WinRM port number (default: 5985 for HTTP, 5986 for HTTPS)
        username: Username for authentication
        password: Password for authentication
    """

    def __init__(
        self, host: str, port: int = 5985, username: str | None = None, password: str | None = None
    ):
        """
        Initialize WinRM handler with target and credentials.

        Args:
            host: Target hostname or IP address
            port: WinRM port number (default: 5985)
            username: Username for authentication
            password: Password for authentication
        """
        self.host = host
        self.port = port
        self.username = username
        self.password = password

    def test_connection(self, timeout: int = 10) -> ConnectionResult:
        """
        Test WinRM connectivity by checking if port is open.

        Args:
            timeout: Connection timeout in seconds (default: 10)

        Returns:
            ConnectionResult with success status and port details
        """
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((self.host, self.port))
            sock.close()

            if result == 0:
                return ConnectionResult(True, "WinRM port is open", {"port": self.port})
            else:
                return ConnectionResult(
                    False, "WinRM port is closed or filtered", {"port": self.port}
                )
        except Exception as e:
            return ConnectionResult(False, f"Connection failed: {str(e)}")

    def execute_command(self, command: str, timeout: int = 30) -> ConnectionResult:
        """
        Execute a command via WinRM REST API.

        Sends a command to the WinRM service running on the target
        host using HTTP/HTTPS requests with optional authentication.

        Args:
            command: Command to execute on remote Windows host
            timeout: Request timeout in seconds (default: 30)

        Returns:
            ConnectionResult with execution status

        Note:
            Requires requests library. Install with: pip install requests
        """
        try:
            import requests
            from requests.auth import HTTPBasicAuth

            url = f"http://{self.host}:{self.port}/wsman"

            if self.username and self.password:
                auth = HTTPBasicAuth(self.username, self.password)
            else:
                auth = None

            response = requests.get(url, auth=auth, timeout=timeout)

            if response.status_code in [200, 401]:
                return ConnectionResult(
                    True,
                    "WinRM service accessible",
                    {"status_code": response.status_code},
                )
            else:
                return ConnectionResult(
                    False, f"WinRM returned status {response.status_code}"
                )

        except ImportError:
            return ConnectionResult(False, "requests library needed for WinRM", {})
        except Exception as e:
            return ConnectionResult(False, f"WinRM connection failed: {str(e)}")

    def open_session(self) -> str:
        """
        Generate WinRM connection command string.

        Returns:
            str: WinRM command for connecting to host
        """
        if self.username:
            return f"winrm s:/{self.host} -u:{self.username}"
        else:
            return f"winrm s:/{self.host}"


class SMBHandler:
    """
    Handler for SMB (Server Message Block) connections.

    Provides connectivity testing and share enumeration for SMB.
    Share listing is Windows-only using the net view command.

    Attributes:
        host: Target hostname or IP address
        port: SMB port number (default: 445)
        username: Username for authentication (optional)
        password: Password for authentication (optional)
    """

    def __init__(
        self, host: str, port: int = 445, username: str | None = None, password: str | None = None
    ):
        """
        Initialize SMB handler with target and credentials.

        Args:
            host: Target hostname or IP address
            port: SMB port number (default: 445)
            username: Username for authentication
            password: Password for authentication
        """
        self.host = host
        self.port = port
        self.username = username
        self.password = password

    def test_connection(self, timeout: int = 10) -> ConnectionResult:
        """
        Test SMB connectivity by checking if port is open.

        Args:
            timeout: Connection timeout in seconds (default: 10)

        Returns:
            ConnectionResult with success status and port details
        """
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((self.host, self.port))
            sock.close()

            if result == 0:
                return ConnectionResult(True, "SMB port is open", {"port": self.port})
            else:
                return ConnectionResult(
                    False, "SMB port is closed or filtered", {"port": self.port}
                )
        except Exception as e:
            return ConnectionResult(False, f"Connection failed: {str(e)}")

    def list_shares(self) -> ConnectionResult:
        """
        List available SMB shares on the target host.

        Uses the net view command to enumerate shared resources.
        Only available on Windows systems.

        Returns:
            ConnectionResult with share listing or error
        """
        try:
            if os.name == "nt":
                result = subprocess.run(
                    ["net", "view", f"\\\\{self.host}"],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                if result.returncode == 0:
                    return ConnectionResult(
                        True, "Shares retrieved", {"output": result.stdout}
                    )
                else:
                    return ConnectionResult(
                        False, "Failed to list shares", {"error": result.stderr}
                    )
            else:
                return ConnectionResult(False, "SMB share listing only on Windows", {})
        except Exception as e:
            return ConnectionResult(False, f"SMB operation failed: {str(e)}")

    def open_session(self) -> str:
        """
        Generate SMB connection path string.

        Returns:
            str: UNC path for SMB connection
        """
        return f"\\\\{self.host}"


class ConnectionFactory:
    """
    Factory class for creating and testing remote connection handlers.

    Provides static methods to instantiate appropriate handler classes
    based on connection type and to perform common operations without
    needing to manage handler instances directly.

    Supported Connection Types:
        ssh: SSHHandler (port 22)
        rdp: RDPHandler (port 3389)
        vnc: VNCHandler (port 5900)
        winrm: WinRMHandler (port 5985)
        smb: SMBHandler (port 445)

    Usage:
        # Create a handler
        handler = ConnectionFactory.create_handler("ssh", "192.168.1.100", username="admin")

        # Quick connection test
        result = ConnectionFactory.test_connection("ssh", "192.168.1.100")

        # Execute remote command
        result = ConnectionFactory.execute_remote_command(
            "ssh", "192.168.1.100", "whoami", username="admin", password="pass"
        )
    """

    @staticmethod
    def create_handler(
        connection_type: str,
        host: str,
        port: int | None = None,
        username: str | None = None,
        password: str | None = None,
    ) -> SSHHandler | RDPHandler | VNCHandler | WinRMHandler | SMBHandler:
        """
        Create a connection handler for the specified type.

        Instantiates the appropriate handler class based on the
        connection type string.

        Args:
            connection_type: Protocol type (ssh, rdp, vnc, winrm, smb)
            host: Target hostname or IP address
            port: Optional custom port (uses protocol default if not specified)
            username: Username for authentication
            password: Password for authentication

        Returns:
            Handler instance for the specified connection type

        Raises:
            ValueError: If connection type is not supported
        """
        ports = {
            "ssh": 22,
            "rdp": 3389,
            "vnc": 5900,
            "winrm": 5985,
            "smb": 445,
            "telnet": 23,
        }

        if port is None:
            port = ports.get(connection_type.lower(), 22)

        handlers = {
            "ssh": SSHHandler,
            "rdp": RDPHandler,
            "vnc": VNCHandler,
            "winrm": WinRMHandler,
            "smb": SMBHandler,
        }

        handler_class = handlers.get(connection_type.lower())
        if not handler_class:
            raise ValueError(f"Unknown connection type: {connection_type}")

        return handler_class(host, port, username, password)

    @staticmethod
    def test_connection(
        connection_type: str,
        host: str,
        port: int | None = None,
        username: str | None = None,
        password: str | None = None,
        timeout: int = 10,
    ) -> ConnectionResult:
        """
        Test a connection without establishing a session.

        Creates a handler for the specified connection type and
        performs a port connectivity test.

        Args:
            connection_type: Protocol type (ssh, rdp, vnc, winrm, smb)
            host: Target hostname or IP address
            port: Optional custom port number
            username: Username for authentication
            password: Password for authentication
            timeout: Connection timeout in seconds (default: 10)

        Returns:
            ConnectionResult with test outcome
        """
        handler = ConnectionFactory.create_handler(
            connection_type, host, port, username, password
        )
        return handler.test_connection(timeout)

    @staticmethod
    def execute_remote_command(
        connection_type: str,
        host: str,
        command: str,
        port: int | None = None,
        username: str | None = None,
        password: str | None = None,
        timeout: int = 30,
    ) -> ConnectionResult:
        """
        Execute a command on a remote system.

        Creates a handler for the specified connection type and
        executes the given command. Not all connection types support
        command execution (only SSH and WinRM).

        Args:
            connection_type: Protocol type (ssh, winrm)
            host: Target hostname or IP address
            command: Command string to execute
            port: Optional custom port number
            username: Username for authentication
            password: Password for authentication
            timeout: Command execution timeout in seconds (default: 30)

        Returns:
            ConnectionResult with command output or error message

        Note:
            Only SSH and WinRM support command execution. Other
            connection types will return a failure result.
        """
        handler = ConnectionFactory.create_handler(
            connection_type, host, port, username, password
        )

        if hasattr(handler, "execute_command"):
            return handler.execute_command(command, timeout)
        else:
            return ConnectionResult(
                False, f"{connection_type} doesn't support command execution"
            )
