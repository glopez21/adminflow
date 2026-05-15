"""Unit tests for AD Security Auditor."""

from unittest.mock import Mock


class TestADSecurityAuditorSchema:
    """Schema validation tests for ADSecurityAuditor."""

    def test_auditor_init(self):
        from src.security.ad_security import ADSecurityAuditor

        mock_conn = Mock()
        mock_conn.server = "dc01.domain.com"
        mock_conn.base_dn = "dc=domain,dc=com"

        auditor = ADSecurityAuditor(mock_conn)
        assert auditor.conn == mock_conn
        assert auditor.pyad is None


class TestSecurityAuditorMethods:
    """Test that required methods exist and return correct types."""

    def test_required_methods_exist(self):
        from src.security.ad_security import ADSecurityAuditor

        mock_conn = Mock()
        auditor = ADSecurityAuditor(mock_conn)

        assert hasattr(auditor, "find_privileged_accounts")
        assert hasattr(auditor, "check_password_policy_compliance")
        assert hasattr(auditor, "find_inactive_accounts")
        assert hasattr(auditor, "find_locked_accounts")
        assert hasattr(auditor, "audit_security_groups")
        assert hasattr(auditor, "generate_security_report")

    def test_find_privileged_accounts_returns_list(self):
        from src.security.ad_security import ADSecurityAuditor

        mock_conn = Mock()
        auditor = ADSecurityAuditor(mock_conn)
        result = auditor.find_privileged_accounts()

        assert isinstance(result, list)

    def test_check_password_policy_compliance_returns_dict(self):
        from src.security.ad_security import ADSecurityAuditor

        mock_conn = Mock()
        auditor = ADSecurityAuditor(mock_conn)
        result = auditor.check_password_policy_compliance()

        assert isinstance(result, dict)
        assert "status" in result

    def test_find_inactive_accounts_returns_list(self):
        from src.security.ad_security import ADSecurityAuditor

        mock_conn = Mock()
        auditor = ADSecurityAuditor(mock_conn)
        result = auditor.find_inactive_accounts(90)

        assert isinstance(result, list)

    def test_find_inactive_accounts_default_days(self):
        from src.security.ad_security import ADSecurityAuditor

        mock_conn = Mock()
        auditor = ADSecurityAuditor(mock_conn)
        result = auditor.find_inactive_accounts()

        assert isinstance(result, list)

    def test_find_locked_accounts_returns_list(self):
        from src.security.ad_security import ADSecurityAuditor

        mock_conn = Mock()
        auditor = ADSecurityAuditor(mock_conn)
        result = auditor.find_locked_accounts()

        assert isinstance(result, list)

    def test_audit_security_groups_returns_dict(self):
        from src.security.ad_security import ADSecurityAuditor

        mock_conn = Mock()
        auditor = ADSecurityAuditor(mock_conn)
        result = auditor.audit_security_groups()

        assert isinstance(result, dict)

    def test_generate_security_report_returns_dict(self):
        from src.security.ad_security import ADSecurityAuditor

        mock_conn = Mock()
        mock_conn.base_dn = "dc=domain,dc=com"
        auditor = ADSecurityAuditor(mock_conn)
        result = auditor.generate_security_report()

        assert isinstance(result, dict)
        assert "timestamp" in result
        assert "domain" in result
        assert "checks" in result
        assert "overall_status" in result
