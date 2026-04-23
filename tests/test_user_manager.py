"""
Unit tests for AD User Manager.

These tests use mocking to avoid requiring actual AD connectivity.
On non-Windows systems, pyad throws an exception, so we test accordingly.
"""

from unittest.mock import Mock


class TestADUserManagerSchema:
    """Schema validation tests for ADUserManager."""

    def test_manager_init(self):
        """Test manager initialization."""
        from src.user_management.ad_user_manager import ADUserManager

        mock_conn = Mock()
        mock_conn.server = "dc01.domain.com"
        mock_conn.base_dn = "dc=domain,dc=com"

        manager = ADUserManager(mock_conn)
        assert manager.conn == mock_conn
        assert manager.pyad is None


class TestUserManagerMethods:
    """Test that required methods exist."""

    def test_required_methods_exist(self):
        """Test all required methods are defined."""
        from src.user_management.ad_user_manager import ADUserManager

        mock_conn = Mock()
        manager = ADUserManager(mock_conn)

        assert hasattr(manager, "create_user")
        assert hasattr(manager, "disable_user")
        assert hasattr(manager, "enable_user")
        assert hasattr(manager, "reset_password")
        assert hasattr(manager, "move_user")
        assert hasattr(manager, "get_user_info")
        assert hasattr(manager, "find_inactive_users")
        assert hasattr(manager, "bulk_create_users")

    def test_create_user_returns_dict(self):
        """Test create_user returns proper dict structure."""
        from src.user_management.ad_user_manager import ADUserManager

        mock_conn = Mock()
        mock_conn.server = "dc01.domain.com"
        mock_conn.base_dn = "dc=domain,dc=com"

        manager = ADUserManager(mock_conn)
        result = manager.create_user(
            username="jsmith",
            first_name="John",
            last_name="Smith",
            email="jsmith@domain.com",
            password="Password123!",
            ou="OU=Users,DC=domain,DC=com",
        )

        assert isinstance(result, dict)
        assert "status" in result
        assert result["status"] == "error"

    def test_disable_user_returns_dict(self):
        """Test disable_user returns proper dict structure."""
        from src.user_management.ad_user_manager import ADUserManager

        mock_conn = Mock()
        manager = ADUserManager(mock_conn)
        result = manager.disable_user("jsmith")

        assert isinstance(result, dict)
        assert "status" in result

    def test_enable_user_returns_dict(self):
        """Test enable_user returns proper dict structure."""
        from src.user_management.ad_user_manager import ADUserManager

        mock_conn = Mock()
        manager = ADUserManager(mock_conn)
        result = manager.enable_user("jsmith")

        assert isinstance(result, dict)
        assert "status" in result

    def test_reset_password_returns_dict(self):
        """Test reset_password returns proper dict structure."""
        from src.user_management.ad_user_manager import ADUserManager

        mock_conn = Mock()
        manager = ADUserManager(mock_conn)
        result = manager.reset_password("jsmith", "NewPassword123!")

        assert isinstance(result, dict)
        assert "status" in result

    def test_move_user_returns_dict(self):
        """Test move_user returns proper dict structure."""
        from src.user_management.ad_user_manager import ADUserManager

        mock_conn = Mock()
        manager = ADUserManager(mock_conn)
        result = manager.move_user("jsmith", "OU=Archive,DC=domain,DC=com")

        assert isinstance(result, dict)
        assert "status" in result

    def test_get_user_info_returns_dict(self):
        """Test get_user_info returns proper dict structure."""
        from src.user_management.ad_user_manager import ADUserManager

        mock_conn = Mock()
        manager = ADUserManager(mock_conn)
        result = manager.get_user_info("jsmith")

        assert isinstance(result, dict)
        assert "status" in result

    def test_find_inactive_users_returns_list(self):
        """Test find_inactive_users returns proper list."""
        from src.user_management.ad_user_manager import ADUserManager

        mock_conn = Mock()
        manager = ADUserManager(mock_conn)
        result = manager.find_inactive_users(90)

        assert isinstance(result, list)

    def test_bulk_create_users(self):
        """Test bulk_create_users returns results."""
        from src.user_management.ad_user_manager import ADUserManager

        mock_conn = Mock()
        manager = ADUserManager(mock_conn)

        users = [
            {
                "username": "user1",
                "first_name": "User",
                "last_name": "One",
                "email": "user1@domain.com",
                "password": "Pass123!",
                "ou": "OU=Users,DC=domain,DC=com",
            },
        ]

        result = manager.bulk_create_users(users)

        assert isinstance(result, dict)
        assert "success" in result
        assert "failed" in result
