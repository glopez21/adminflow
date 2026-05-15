"""Unit tests for AD Health Checker."""

from unittest.mock import Mock


class TestADHealthCheckerSchema:
    """Schema validation tests for ADHealthChecker."""

    def test_checker_init(self):
        from src.health_checks.ad_health import ADHealthChecker

        mock_conn = Mock()
        mock_conn.server = "dc01.domain.com"
        mock_conn.base_dn = "dc=domain,dc=com"

        checker = ADHealthChecker(mock_conn)
        assert checker.conn == mock_conn


class TestHealthCheckerMethods:
    """Test that required methods exist and return correct types."""

    def test_required_methods_exist(self):
        from src.health_checks.ad_health import ADHealthChecker

        mock_conn = Mock()
        checker = ADHealthChecker(mock_conn)

        assert hasattr(checker, "check_domain_controllers")
        assert hasattr(checker, "check_replication")
        assert hasattr(checker, "check_ldap_connectivity")
        assert hasattr(checker, "check_fsmo_roles")
        assert hasattr(checker, "check_dns_records")
        assert hasattr(checker, "generate_health_report")

    def test_check_domain_controllers_returns_list(self):
        from src.health_checks.ad_health import ADHealthChecker

        mock_conn = Mock()
        checker = ADHealthChecker(mock_conn)
        result = checker.check_domain_controllers()

        assert isinstance(result, list)

    def test_check_replication_returns_dict(self):
        from src.health_checks.ad_health import ADHealthChecker

        mock_conn = Mock()
        checker = ADHealthChecker(mock_conn)
        result = checker.check_replication()

        assert isinstance(result, dict)
        assert "status" in result
        assert "timestamp" in result

    def test_check_ldap_connectivity_returns_dict(self):
        from src.health_checks.ad_health import ADHealthChecker

        mock_conn = Mock()
        mock_conn.server = "dc01.domain.com"
        checker = ADHealthChecker(mock_conn)

        result = checker.check_ldap_connectivity()

        assert isinstance(result, dict)
        assert "status" in result
        assert "server" in result

    def test_check_ldap_connectivity_with_custom_server(self):
        from src.health_checks.ad_health import ADHealthChecker

        mock_conn = Mock()
        mock_conn.server = "dc01.domain.com"
        checker = ADHealthChecker(mock_conn)

        result = checker.check_ldap_connectivity(server="dc02.domain.com")

        assert isinstance(result, dict)
        assert result.get("server") == "dc02.domain.com"

    def test_check_fsmo_roles_returns_dict(self):
        from src.health_checks.ad_health import ADHealthChecker

        mock_conn = Mock()
        checker = ADHealthChecker(mock_conn)
        result = checker.check_fsmo_roles()

        assert isinstance(result, dict)

    def test_check_dns_records_returns_dict(self):
        from src.health_checks.ad_health import ADHealthChecker

        mock_conn = Mock()
        mock_conn.base_dn = "dc=domain,dc=com"
        checker = ADHealthChecker(mock_conn)
        result = checker.check_dns_records()

        assert isinstance(result, dict)

    def test_generate_health_report_returns_dict(self):
        from src.health_checks.ad_health import ADHealthChecker

        mock_conn = Mock()
        mock_conn.server = "dc01.domain.com"
        mock_conn.base_dn = "dc=domain,dc=com"
        checker = ADHealthChecker(mock_conn)
        result = checker.generate_health_report()

        assert isinstance(result, dict)
        assert "timestamp" in result
        assert "domain" in result
        assert "checks" in result
        assert "overall_status" in result
