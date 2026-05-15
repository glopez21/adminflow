"""
Systems and Remote Connection API Endpoints for AdminFlow.

This module provides REST API endpoints for managing the system inventory
and testing remote connectivity to various services. It supports adding
systems to inventory, listing with filters, updating, and deleting systems.
Additionally provides connectivity testing for SSH, RDP, VNC, WinRM, SMB,
and general port scanning capabilities.

Endpoints:
    POST /api/systems/ - Add a system to inventory
    GET /api/systems/ - List all systems with optional filters
    GET /api/systems/{system_id} - Get system details
    PUT /api/systems/{system_id} - Update system information
    DELETE /api/systems/{system_id} - Remove system from inventory
    POST /api/systems/remote-connect - Test remote connectivity
    POST /api/systems/ping - Ping a host
    POST /api/systems/port-scan - Scan ports on a host
    GET /api/systems/types - Get list of system types
    GET /api/systems/services - Get list of common services/ports

Authentication:
    Requires API key or JWT token with appropriate scopes.

Example:
    # Add a system to inventory
    curl -X POST -H "X-API-Key: ad-admin-key-001" \
         -H "Content-Type: application/json" \
         -d '{"hostname": "web-server-01", "ip_address": "192.168.1.100", \
             "system_type": "server", "os": "Ubuntu 22.04"}' \
         http://localhost:8000/api/systems/

    # Test SSH connectivity
    curl -X POST -H "Authorization: Bearer <token>" \
         -H "Content-Type: application/json" \
         -d '{"target_host": "192.168.1.100", "connection_type": "ssh"}' \
         http://localhost:8000/api/systems/remote-connect
"""

import json
import logging
import os
import socket
import subprocess
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

from src.api.models.schemas import RemoteConnectionRequest, SystemCreate, SystemUpdate

logger = logging.getLogger(__name__)
router = APIRouter()

SYSTEMS_DB = "reports/systems.json"


def load_systems() -> list[dict]:
    try:
        if os.path.exists(SYSTEMS_DB):
            with open(SYSTEMS_DB) as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load systems: {e}")
    return []


def save_systems(systems: list[dict]) -> None:
    os.makedirs(os.path.dirname(SYSTEMS_DB), exist_ok=True)
    with open(SYSTEMS_DB, "w") as f:
        json.dump(systems, f, indent=2)


@router.post("/", response_model=dict)
async def add_system(system: SystemCreate):
    """
    Add a new system to the inventory.

    Registers a new system with hostname, IP address, type, and
    optional attributes like OS, description, location, and tags.

    Args:
        system: SystemCreate schema with system details

    Returns:
        dict: Success status and created system information
    """
    systems = load_systems()

    system_data = {
        "id": len(systems) + 1,
        "hostname": system.hostname,
        "ip_address": system.ip_address,
        "system_type": system.system_type,
        "os": system.os,
        "description": system.description,
        "location": system.location,
        "tags": system.tags or [],
        "status": "active",
        "added": datetime.now(timezone.utc).isoformat(),
    }

    systems.append(system_data)
    save_systems(systems)

    return {"status": "success", "system": system_data}


@router.get("/", response_model=dict)
async def list_systems(
    system_type: str | None = None,
    status: str | None = None,
    tag: str | None = None,
):
    """
    List all systems with optional filters.

    Retrieves all systems from inventory, optionally filtered by
    system type, status, or tags.

    Args:
        system_type: Filter by system type (windows, linux, server, etc.)
        status: Filter by status (active, inactive, maintenance)
        tag: Filter by tag name

    Returns:
        dict: Count and list of matching systems

    Example:
        GET /api/systems/?system_type=server&status=active
    """
    systems = load_systems()

    if system_type:
        systems = [s for s in systems if s.get("system_type") == system_type]
    if status:
        systems = [s for s in systems if s.get("status") == status]
    if tag:
        systems = [s for s in systems if tag in s.get("tags", [])]

    return {"count": len(systems), "systems": systems}


@router.get("/{system_id}", response_model=dict)
async def get_system(system_id: int):
    """
    Get detailed information about a specific system.

    Retrieves all stored information about a system by its ID.

    Args:
        system_id: The ID of the system to retrieve

    Returns:
        dict: System details

    Raises:
        HTTPException: If system not found (404)
    """
    systems = load_systems()
    for system in systems:
        if system.get("id") == system_id:
            return system
    raise HTTPException(status_code=404, detail="System not found")


@router.put("/{system_id}")
async def update_system(system_id: int, update: SystemUpdate):
    """
    Update system information.

    Updates one or more attributes of an existing system.
    Only provided fields are updated, others remain unchanged.

    Args:
        system_id: The ID of the system to update
        update: SystemUpdate schema with fields to update

    Returns:
        dict: Success status and updated system information

    Raises:
        HTTPException: If system not found (404)
    """
    systems = load_systems()

    for system in systems:
        if system.get("id") == system_id:
            update_data = update.dict(exclude_unset=True)
            system.update(update_data)
            system["updated"] = datetime.now(timezone.utc).isoformat()
            save_systems(systems)
            return {"status": "success", "system": system}

    raise HTTPException(status_code=404, detail="System not found")


@router.delete("/{system_id}")
async def delete_system(system_id: int):
    """
    Remove a system from the inventory.

    Deletes a system record from the inventory database.

    Args:
        system_id: The ID of the system to delete

    Returns:
        dict: Success status with deleted system ID
    """
    systems = load_systems()
    systems = [s for s in systems if s.get("id") != system_id]
    save_systems(systems)
    return {"status": "success", "deleted": system_id}


@router.post("/remote-connect")
async def remote_connect(request: RemoteConnectionRequest):
    """
    Test remote connectivity to a system.

    Performs connectivity tests for various remote access protocols
    including SSH, RDP, VNC, WinRM, SMB, or simple ping/port checks.

    Args:
        request: RemoteConnectionRequest with connection parameters

    Returns:
        dict: Test results including status and details
    """
    target = request.target_host
    conn_type = request.connection_type
    port = request.port

    result = {
        "target": target,
        "type": conn_type,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "status": "pending",
    }

    try:
        if conn_type == "ping":
            response = ping_host(target)
            result.update(response)

        elif conn_type == "port":
            if not port:
                port = 22
            result_port = check_port(target, port)
            result.update(result_port)

        elif conn_type in ["ssh", "rdp", "vnc", "winrm", "smb"]:
            result_connection = test_connection(target, conn_type, port)
            result.update(result_connection)

        else:
            raise HTTPException(
                status_code=400, detail=f"Unknown connection type: {conn_type}"
            )

        return result

    except Exception as e:
        logger.error(f"Remote connection failed: {e}")
        return {
            "target": target,
            "type": conn_type,
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


@router.post("/ping")
async def ping_host_api(host: str, count: int = 4):
    """
    Ping a host and return results.

    Sends ICMP ping packets to the target host and reports
    packet loss and response status.

    Args:
        host: Hostname or IP address to ping
        count: Number of ping packets to send (default: 4)

    Returns:
        dict: Ping results with status and packet statistics
    """
    result = ping_host(host, count)
    return result


@router.post("/port-scan")
async def port_scan(host: str, ports: list[int] | None = None):
    """
    Scan ports on a host.

    Checks the status of specified ports (or defaults to common ports)
    on the target host to determine which services are available.

    Args:
        host: Hostname or IP address to scan
        ports: Optional list of ports to scan (defaults to common ports)

    Returns:
        dict: Host and list of port results

    Default Ports:
        22 (SSH), 23 (Telnet), 80 (HTTP), 443 (HTTPS), 3389 (RDP),
        445 (SMB), 5985 (WinRM), 8080 (HTTP-Alt)
    """
    if ports is None:
        ports = [22, 23, 80, 443, 3389, 445, 5985, 8080]

    results = []
    for port in ports:
        result = check_port(host, port)
        results.append(result)

    return {"host": host, "ports": results}


def ping_host(host: str, count: int = 4) -> dict:
    """
    Ping a host and return results.

    Executes the system ping command and parses the output
    to determine if the host is reachable.

    Args:
        host: Target hostname or IP address
        count: Number of ping attempts

    Returns:
        dict: Ping status and statistics
    """
    try:
        param = "-n" if os.name == "nt" else "-c"
        command = ["ping", param, str(count), host]

        result = subprocess.run(command, capture_output=True, text=True, timeout=30)

        if result.returncode == 0:
            return {
                "status": "online",
                "target": host,
                "packets_sent": count,
                "packets_received": count,
                "packet_loss": "0%",
            }
        else:
            return {"status": "offline", "target": host, "error": result.stderr}

    except subprocess.TimeoutExpired:
        return {"status": "timeout", "target": host}
    except Exception as e:
        return {"status": "error", "target": host, "error": str(e)}


def check_port(host: str, port: int, timeout: int = 5) -> dict:
    """
    Check if a port is open on a host.

    Attempts a TCP connection to the specified port and
    reports whether it's open, closed, or in error.

    Args:
        host: Target hostname or IP address
        port: Port number to check
        timeout: Connection timeout in seconds

    Returns:
        dict: Port status and service name
    """
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()

        return {
            "host": host,
            "port": port,
            "status": "open" if result == 0 else "closed",
            "service": get_service_name(port),
        }
    except Exception as e:
        return {"host": host, "port": port, "status": "error", "error": str(e)}


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
        995=POP3S, 1433=MSSQL, 3306=MySQL, 3389=RDP,
        5432=PostgreSQL, 5900=VNC, 5985=WinRM, 6379=Redis,
        8080=HTTP-Proxy, 8443=HTTPS-Alt, 27017=MongoDB
    """
    services = {
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


def test_connection(host: str, conn_type: str, port: int | None = None) -> dict:
    """
    Test various remote connection types.

    Performs connectivity tests for specific remote access protocols
    by checking the default port for that protocol.

    Args:
        host: Target hostname or IP address
        conn_type: Connection type (ssh, rdp, vnc, winrm, smb, telnet)
        port: Optional custom port (defaults to protocol standard)

    Returns:
        dict: Connection test results
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
        port = ports.get(conn_type, 22)

    result = check_port(host, port, timeout=10)
    return {"connection_type": conn_type, "port_tested": port, "result": result}


@router.get("/types")
async def get_system_types():
    """
    Get list of supported system types.

    Returns the list of valid system type values that can be
    used when creating or filtering systems in the inventory.

    Returns:
        dict: List of system type identifiers

    Types:
        windows, linux, macos, network, printer, server, storage, iot
    """
    return {
        "types": [
            "windows",
            "linux",
            "macos",
            "network",
            "printer",
            "server",
            "storage",
            "iot",
        ]
    }


@router.get("/services")
async def get_common_services():
    """
    Get list of common services and their port numbers.

    Returns a reference list of commonly used services and
    their associated port numbers for quick reference.

    Returns:
        dict: List of common services with port numbers
    """
    return {
        "services": [
            {"port": 22, "name": "SSH"},
            {"port": 3389, "name": "RDP"},
            {"port": 445, "name": "SMB"},
            {"port": 5985, "name": "WinRM"},
            {"port": 5900, "name": "VNC"},
            {"port": 80, "name": "HTTP"},
            {"port": 443, "name": "HTTPS"},
        ]
    }
