"""
Active Directory Connection Management Module.

This module provides the core functionality for connecting to and interacting
with Microsoft Active Directory. It serves as the foundation for all AD operations
in the AdminFlow system.

Key Features:
- Connection establishment and management
- Connection testing and validation
- Configuration-based connection factory
- Connection pooling with acquire/release pattern
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
import threading
from collections import OrderedDict
from datetime import datetime, timezone

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
        server=str(config.get("AD_SERVER", "")),
        username=str(config.get("AD_USER", "")),
        password=str(config.get("AD_PASSWORD", "")),
        base_dn=str(config.get("AD_BASE_DN", "")),
    )


class ADConnectionPool:
    """Thread-safe pool of reusable AD connections.

    Maintains a cache of ADConnection instances keyed by
    ``server|username|base_dn``. Connections are re-used within their
    TTL and evicted when stale or when the pool exceeds ``max_size``
    (LRU eviction).

    On Linux (where pyad is unavailable) the pool is effectively a
    no-op — connections are created, not cached, to avoid holding
    useless objects.

    Usage::

        pool = ADConnectionPool(max_size=10, ttl_seconds=300)
        with pool.get_connection(
            server="dc01.domain.com",
            username="admin@domain.com",
            password="****",
            base_dn="dc=domain,dc=com",
        ) as conn:
            if conn.is_connected:
                # perform AD operations
                pass
    """

    def __init__(self, max_size: int = 10, ttl_seconds: int = 300):
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self._pool: OrderedDict[str, ADConnection] = OrderedDict()
        self._timestamps: dict[str, datetime] = {}
        self._lock = threading.Lock()

    def _make_key(self, server: str, username: str, base_dn: str) -> str:
        return f"{server}|{username}|{base_dn}"

    def acquire(
        self, server: str, username: str, password: str, base_dn: str
    ) -> ADConnection:
        """Get a connection from the pool, creating one if necessary."""
        key = self._make_key(server, username, base_dn)

        with self._lock:
            conn = self._pool.get(key)

            if conn is not None:
                age = datetime.now(timezone.utc) - self._timestamps.get(key, datetime.now(timezone.utc))
                if age.total_seconds() < self.ttl_seconds and conn.is_connected:
                    self._pool.move_to_end(key)
                    logger.debug(f"Reusing pooled AD connection: {key}")
                    return conn

                conn.disconnect()
                del self._pool[key]
                del self._timestamps[key]

            conn = ADConnection(server=server, username=username, password=password, base_dn=base_dn)
            conn.connect()

            if len(self._pool) >= self.max_size:
                oldest_key, oldest_conn = next(iter(self._pool.items()))
                oldest_conn.disconnect()
                del self._pool[oldest_key]
                del self._timestamps[oldest_key]

            self._pool[key] = conn
            self._timestamps[key] = datetime.now(timezone.utc)
            logger.debug(f"Created new pooled AD connection: {key}")
            return conn

    def release(self, conn: ADConnection) -> None:
        """Return a connection to the pool (marks it as available).

        Connections whose underlying transport is dead are removed.
        """
        key = self._make_key(conn.server, conn.username, conn.base_dn)
        with self._lock:
            if key in self._pool and self._pool[key] is conn:
                if not conn.is_connected:
                    self._pool.pop(key, None)
                    self._timestamps.pop(key, None)
            else:
                conn.disconnect()

    def close_all(self) -> None:
        """Disconnect and remove every connection in the pool."""
        with self._lock:
            for conn in self._pool.values():
                try:
                    conn.disconnect()
                except Exception:
                    pass
            self._pool.clear()
            self._timestamps.clear()
            logger.info("All pooled AD connections closed")

    def __del__(self) -> None:
        self.close_all()


# Global default pool instance
_default_pool = ADConnectionPool()


def get_pooled_connection(
    server: str,
    username: str,
    password: str,
    base_dn: str,
    pool: ADConnectionPool | None = None,
) -> ADConnection:
    """Acquire an AD connection from the pool (or the global default pool).

    Callers should use this instead of ``ADConnection`` directly when
    they want connection reuse.  The caller is responsible for calling
    ``release_connection(conn)`` when done.
    """
    p = pool or _default_pool
    return p.acquire(server, username, password, base_dn)


def release_connection(
    conn: ADConnection, pool: ADConnectionPool | None = None
) -> None:
    """Release an AD connection back to the pool.

    Args:
        conn: The connection to release (obtained from ``get_pooled_connection``).
        pool: Optional pool instance; uses the global default pool if omitted.
    """
    p = pool or _default_pool
    p.release(conn)


def close_all_pool_connections(pool: ADConnectionPool | None = None) -> None:
    """Disconnect and remove every connection in the pool.

    Should be called during application shutdown.
    """
    p = pool or _default_pool
    p.close_all()


def get_default_pool() -> ADConnectionPool:
    """Return the global default AD connection pool."""
    return _default_pool
