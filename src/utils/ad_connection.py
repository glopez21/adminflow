"""
Active Directory Connection Management Module.

This module provides the core functionality for connecting to and interacting
with Microsoft Active Directory. It serves as the foundation for all AD operations
in the AdminFlow system.

Key Features:
- Connection establishment and management
- Connection testing and validation
- Configuration-based connection factory
- Platform-aware (Windows vs Linux)

Requirements:
- Windows: pyad and pywin32 libraries
- Linux: ldap3 library

Usage:
    # Create connection with configuration
    conn = ADConnection(
        server="dc01.domain.com",
        username="admin@domain.com",
        password="password",
        base_dn="dc=domain,dc=com"
    )
    conn.connect()

    # Use connection for operations
    if conn.is_connected:
        # Perform AD operations...
        pass

    # Always disconnect when done
    conn.disconnect()

Note:
    The pyad library only works on Windows. For cross-platform support,
    consider using ldap3 which works on Linux/macOS.
"""

import logging

# Try to import pyad (Windows-only AD library)
# pyad provides Python bindings for Active Directory via COM
try:
    import pyad

    PYWIN32_AVAILABLE = True
except Exception:
    PYWIN32_AVAILABLE = False

# Get module logger
logger = logging.getLogger(__name__)


class ADConnection:
    """
    Manages the connection to an Active Directory domain.

    This class handles the lifecycle of an AD connection including:
    - Initializing connection parameters
    - Establishing connection to domain controller
    - Testing connectivity
    - Clean disconnection

    Attributes:
        server: Domain controller hostname or IP address
        username: Username for authentication (format: user@domain.com)
        password: Password for authentication
        base_dn: Base Distinguished Name for AD queries
        _connected: Internal flag tracking connection state

    Example:
        >>> conn = ADConnection(
        ...     server="dc01.example.com",
        ...     username="admin@example.com",
        ...     password="SecretPassword123",
        ...     base_dn="dc=example,dc=com"
        ... )
        >>> conn.connect()
        >>> print(f"Connected: {conn.is_connected}")
        True
    """

    def __init__(self, server: str, username: str, password: str, base_dn: str):
        """
        Initialize AD connection with credentials and configuration.

        Args:
            server: Domain controller hostname or IP address
                   Example: "dc01.yourdomain.com" or "192.168.1.10"
            username: Username in UPN format (user@domain.com)
                     or NT format (domain\\username)
            password: User's password
            base_dn: Base Distinguished Name for the domain
                    Example: "dc=yourdomain,dc=com"
        """
        self.server = server
        self.username = username
        self.password = password
        self.base_dn = base_dn
        self._connected = False  # Track connection state

    def connect(self) -> bool:
        """
        Establish connection to Active Directory.

        This method configures pyad defaults with the provided credentials
        and establishes a connection to the specified domain controller.

        Returns:
            bool: True if connection successful, False otherwise

        Note:
            On Linux/macOS, this will return False with a warning since
            pyad is Windows-only. Consider using ldap3 for
            cross-platform compatibility.
        """
        try:
            if PYWIN32_AVAILABLE:
                # Configure pyad with connection parameters
                # This sets defaults used by all pyad operations
                pyad.set_defaults(
                    ldap_server=self.server,
                    username=self.username,
                    password=self.password,
                )

                # Mark as connected (pyad doesn't have explicit connect)
                self._connected = True

                logger.info(f"Successfully connected to AD server: {self.server}")
                return True
            else:
                # pyad not available (non-Windows system)
                logger.warning(
                    "pyad library not available. This module requires Windows "
                    "with pywin32 installed. For Linux/macOS, use ldap3."
                )
                return False

        except Exception as e:
            # Connection failed - log error and return failure
            logger.error(f"Failed to connect to AD server {self.server}: {e}")
            self._connected = False
            return False

    def disconnect(self):
        """
        Close the AD connection and clean up resources.

        Since pyad uses connection pooling internally and doesn't have
        an explicit disconnect method, this primarily updates the
        internal connection state flag.
        """
        self._connected = False
        logger.info(f"Disconnected from AD server: {self.server}")

    def test_connection(self) -> bool:
        """
        Test connectivity to Active Directory.

        Attempts to verify that the AD connection is actually working
        by performing a simple query against the base DN.

        Returns:
            bool: True if connection test successful, False otherwise

        Example:
            >>> conn = ADConnection(...)
            >>> conn.connect()
            >>> if conn.test_connection():
            ...     print("AD connection verified!")
        """
        try:
            if PYWIN32_AVAILABLE:
                # Import here to avoid module-level import issues
                from pyad import pyadobject

                # Try to fetch an object from base DN
                # This will fail if connection is not working
                pyadobject.PyADObject.from_dn(self.base_dn)
                return True

            # Can't test without pyad
            return False

        except Exception as e:
            logger.error(f"AD connection test failed: {e}")
            return False

    @property
    def is_connected(self) -> bool:
        """
        Check if currently connected to AD.

        Property that returns the current connection state.

        Returns:
            bool: True if connected, False otherwise
        """
        return self._connected


def get_ad_connection(config: dict) -> ADConnection:
    """
    Factory function to create AD connection from configuration dictionary.

    This convenience function creates an ADConnection instance using
    values from a configuration dictionary. This is useful when loading
    configuration from files or environment variables.

    Args:
        config: Dictionary with connection parameters
               Expected keys:
               - AD_SERVER: Domain controller hostname
               - AD_USER: Username for authentication
               - AD_PASSWORD: Password
               - AD_BASE_DN: Base Distinguished Name

    Returns:
        ADConnection: Configured connection object (not yet connected)

    Example:
        >>> config = {
        ...     "AD_SERVER": "dc01.example.com",
        ...     "AD_USER": "admin@example.com",
        ...     "AD_PASSWORD": "password",
        ...     "AD_BASE_DN": "dc=example,dc=com"
        ... }
        >>> conn = get_ad_connection(config)
        >>> conn.connect()
    """
    return ADConnection(
        server=config.get("AD_SERVER"),
        username=config.get("AD_USER"),
        password=config.get("AD_PASSWORD"),
        base_dn=config.get("AD_BASE_DN"),
    )
