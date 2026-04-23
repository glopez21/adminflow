"""Unit tests for Pydantic schemas."""

import pytest
from pydantic import ValidationError

from src.api.models.schemas import (
    GroupCreate,
    GroupMemberAdd,
    HealthCheckRequest,
    NetworkScanRequest,
    RemoteConnectionRequest,
    SystemCreate,
    SystemUpdate,
    UserCreate,
    UserResponse,
    UserUpdate,
)


class TestUserCreate:
    """Tests for UserCreate schema."""

    def test_valid_user_create(self):
        """Test creating user with all valid fields."""
        user = UserCreate(
            username="jsmith",
            first_name="John",
            last_name="Smith",
            email="jsmith@company.com",
            password="SecurePass123!",
            department="IT",
            title="Software Engineer",
        )
        assert user.username == "jsmith"
        assert user.first_name == "John"
        assert user.email == "jsmith@company.com"

    def test_valid_user_minimal(self):
        """Test creating user with minimal required fields."""
        user = UserCreate(
            username="jsmith",
            first_name="John",
            last_name="Smith",
            email="jsmith@company.com",
            password="SecurePass123!",
        )
        assert user.username == "jsmith"
        assert user.enabled is True

    def test_invalid_email(self):
        """Test that invalid email is rejected."""
        with pytest.raises(ValidationError):
            UserCreate(
                username="jsmith",
                first_name="John",
                last_name="Smith",
                email="not-an-email",
                password="SecurePass123!",
            )

    def test_required_fields(self):
        """Test that required fields are enforced."""
        with pytest.raises(ValidationError):
            UserCreate(
                username="jsmith",
                first_name="John",
                password="SecurePass123!",
            )


class TestUserUpdate:
    """Tests for UserUpdate schema."""

    def test_partial_update(self):
        """Test updating with partial fields."""
        update = UserUpdate(
            department="Engineering",
            title="Senior Engineer",
        )
        assert update.department == "Engineering"
        assert update.title == "Senior Engineer"
        assert update.first_name is None

    def test_all_optional(self):
        """Test that all fields are optional."""
        update = UserUpdate()
        assert update.first_name is None
        assert update.last_name is None
        assert update.email is None


class TestUserResponse:
    """Tests for UserResponse schema."""

    def test_user_response(self):
        """Test user response schema."""
        response = UserResponse(
            username="jsmith",
            email="jsmith@company.com",
            display_name="John Smith",
            department="IT",
            title="Engineer",
            enabled=True,
        )
        assert response.username == "jsmith"
        assert response.enabled is True


class TestGroupCreate:
    """Tests for GroupCreate schema."""

    def test_valid_group(self):
        """Test creating group with required fields."""
        group = GroupCreate(
            name="IT-Admins",
        )
        assert group.name == "IT-Admins"
        assert group.group_scope == "Global"
        assert group.group_type == "Security"

    def test_group_with_options(self):
        """Test creating group with all options."""
        group = GroupCreate(
            name="IT-Admins",
            group_scope="Universal",
            group_type="Distribution",
            ou="OU=Groups,DC=domain,DC=com",
        )
        assert group.group_scope == "Universal"
        assert group.group_type == "Distribution"


class TestGroupMemberAdd:
    """Tests for GroupMemberAdd schema."""

    def test_valid_member(self):
        """Test adding group member."""
        member = GroupMemberAdd(
            group_name="IT-Admins",
            member_dn="CN=John Smith,OU=Users,DC=domain,DC=com",
        )
        assert member.group_name == "IT-Admins"


class TestSystemCreate:
    """Tests for SystemCreate schema."""

    def test_valid_system(self):
        """Test creating system with required fields."""
        system = SystemCreate(
            hostname="ws-001",
            ip_address="192.168.1.10",
            system_type="windows",
        )
        assert system.hostname == "ws-001"
        assert system.system_type == "windows"

    def test_system_with_optional(self):
        """Test creating system with optional fields."""
        system = SystemCreate(
            hostname="ws-001",
            ip_address="192.168.1.10",
            system_type="windows",
            os="Windows 11 Pro",
            description="Developer workstation",
            location="Office 101",
            tags=["development", "primary"],
        )
        assert system.os == "Windows 11 Pro"
        assert len(system.tags) == 2


class TestSystemUpdate:
    """Tests for SystemUpdate schema."""

    def test_partial_update(self):
        """Test updating with partial fields."""
        update = SystemUpdate(
            status="maintenance",
            tags=["repair"],
        )
        assert update.status == "maintenance"
        assert update.hostname is None


class TestRemoteConnectionRequest:
    """Tests for RemoteConnectionRequest schema."""

    def test_valid_connection(self):
        """Test remote connection request."""
        req = RemoteConnectionRequest(
            target_host="192.168.1.10",
            connection_type="ssh",
            port=22,
            timeout=10,
        )
        assert req.target_host == "192.168.1.10"
        assert req.connection_type == "ssh"

    def test_default_port(self):
        """Test that default port is used when not specified."""
        req = RemoteConnectionRequest(
            target_host="192.168.1.10",
            connection_type="rdp",
        )
        assert req.port is None
        assert req.timeout == 30


class TestNetworkScanRequest:
    """Tests for NetworkScanRequest schema."""

    def test_valid_scan(self):
        """Test network scan request."""
        req = NetworkScanRequest(
            network_range="192.168.1.0/24",
            scan_types=["ping", "port"],
        )
        assert req.network_range == "192.168.1.0/24"

    def test_with_custom_ports(self):
        """Test scan with custom ports."""
        req = NetworkScanRequest(
            network_range="10.0.0.0/24",
            scan_types=["port"],
            ports=[22, 80, 443, 3389],
        )
        assert len(req.ports) == 4


class TestHealthCheckRequest:
    """Tests for HealthCheckRequest schema."""

    def test_valid_check(self):
        """Test health check request."""
        req = HealthCheckRequest(
            target="dc01.domain.com",
            check_type="ping",
        )
        assert req.target == "dc01.domain.com"

    def test_with_port(self):
        """Test health check with port."""
        req = HealthCheckRequest(
            target="dc01.domain.com",
            check_type="port",
            port=389,
            timeout=5,
        )
        assert req.port == 389
        assert req.timeout == 5
