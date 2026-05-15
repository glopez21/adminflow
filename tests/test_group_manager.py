"""Unit tests for AD Group Manager."""

from unittest.mock import Mock


class TestADGroupManagerSchema:
    """Schema validation tests for ADGroupManager."""

    def test_manager_init(self):
        from src.user_management.group_management import ADGroupManager

        mock_conn = Mock()
        mock_conn.server = "dc01.domain.com"
        mock_conn.base_dn = "dc=domain,dc=com"

        manager = ADGroupManager(mock_conn)
        assert manager.conn == mock_conn
        assert manager.pyad is None


class TestGroupManagerMethods:
    """Test that required methods exist and return correct types."""

    def test_required_methods_exist(self):
        from src.user_management.group_management import ADGroupManager

        mock_conn = Mock()
        manager = ADGroupManager(mock_conn)

        assert hasattr(manager, "create_group")
        assert hasattr(manager, "add_member")
        assert hasattr(manager, "remove_member")
        assert hasattr(manager, "get_group_members")
        assert hasattr(manager, "get_user_groups")
        assert hasattr(manager, "find_empty_groups")
        assert hasattr(manager, "bulk_add_members")

    def test_create_group_returns_dict(self):
        from src.user_management.group_management import ADGroupManager

        mock_conn = Mock()
        mock_conn.server = "dc01.domain.com"
        mock_conn.base_dn = "dc=domain,dc=com"

        manager = ADGroupManager(mock_conn)
        result = manager.create_group("TestGroup", "Global", "Security")

        assert isinstance(result, dict)
        assert result["status"] == "error"

    def test_create_group_with_ou(self):
        from src.user_management.group_management import ADGroupManager

        mock_conn = Mock()
        mock_conn.base_dn = "dc=domain,dc=com"

        manager = ADGroupManager(mock_conn)
        result = manager.create_group(
            "TestGroup", "Universal", "Distribution",
            ou="OU=Groups,DC=domain,DC=com"
        )

        assert isinstance(result, dict)
        assert "status" in result

    def test_add_member_returns_dict(self):
        from src.user_management.group_management import ADGroupManager

        mock_conn = Mock()
        manager = ADGroupManager(mock_conn)
        result = manager.add_member("TestGroup", "CN=User,DC=domain,DC=com")

        assert isinstance(result, dict)
        assert "status" in result

    def test_remove_member_returns_dict(self):
        from src.user_management.group_management import ADGroupManager

        mock_conn = Mock()
        manager = ADGroupManager(mock_conn)
        result = manager.remove_member("TestGroup", "CN=User,DC=domain,DC=com")

        assert isinstance(result, dict)
        assert "status" in result

    def test_get_group_members_returns_list(self):
        from src.user_management.group_management import ADGroupManager

        mock_conn = Mock()
        manager = ADGroupManager(mock_conn)
        result = manager.get_group_members("Domain-Admins")

        assert isinstance(result, list)

    def test_get_user_groups_returns_list(self):
        from src.user_management.group_management import ADGroupManager

        mock_conn = Mock()
        manager = ADGroupManager(mock_conn)
        result = manager.get_user_groups("jsmith")

        assert isinstance(result, list)

    def test_find_empty_groups_returns_list(self):
        from src.user_management.group_management import ADGroupManager

        mock_conn = Mock()
        manager = ADGroupManager(mock_conn)
        result = manager.find_empty_groups()

        assert isinstance(result, list)

    def test_bulk_add_members_returns_dict(self):
        from src.user_management.group_management import ADGroupManager

        mock_conn = Mock()
        manager = ADGroupManager(mock_conn)
        result = manager.bulk_add_members("TestGroup", ["CN=User1,DC=domain,DC=com"])

        assert isinstance(result, dict)
        assert "success" in result
        assert "failed" in result
