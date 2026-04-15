"""
AdminFlow Configuration Settings.

This module contains all configuration parameters for the AdminFlow
Active Directory automation system. These settings control AD connection,
password policies, thresholds, and output paths.

Configuration Areas:
    - AD Connection: Server, credentials, and base DN settings
    - LDAP: Port configuration for LDAP/LDAPS
    - Defaults: Default OU and group for new objects
    - Password Policy: Requirements and lockout settings
    - Inactive Threshold: Days before accounts are flagged inactive
    - Output: Report and log file directories

Security Note:
    IMPORTANT: AD_PASSWORD should be set via environment variable in
    production. Never commit credentials to version control.

    Environment variables can override these settings:
        AD_SERVER, AD_USER, AD_PASSWORD, AD_BASE_DN

Usage:
    import config.settings as settings

    server = settings.AD_SERVER
    password_policy = settings.PASSWORD_POLICY
"""

# ============================================================================
# ACTIVE DIRECTORY CONNECTION SETTINGS
# ============================================================================
# Configure these to match your AD environment.
# IMPORTANT: Set AD_PASSWORD via environment variable in production!

AD_SERVER = "dc01.yourdomain.com"
AD_BASE_DN = "dc=yourdomain,dc=com"
AD_USER = "admin@yourdomain.com"
AD_PASSWORD = ""

# ============================================================================
# LDAP PORT CONFIGURATION
# ============================================================================
# Standard LDAP and LDAPS port numbers

LDAP_PORT = 389
LDAPS_PORT = 636

# ============================================================================
# DEFAULT ORGANIZATIONAL UNIT AND GROUP
# ============================================================================
# Default OU for new user creation and default group assignment

DEFAULT_OU = "ou=Users,dc=yourdomain,dc=com"
DEFAULT_GROUP = "Domain Users"

# ============================================================================
# PASSWORD POLICY REQUIREMENTS
# ============================================================================
# Defines the password requirements for the AD environment.
# Used for compliance checking in security audits.

PASSWORD_POLICY = {
    "min_length": 12,
    "require_uppercase": True,
    "require_lowercase": True,
    "require_numbers": True,
    "require_special": True,
    "max_age_days": 90,
    "min_age_days": 1,
    "lockout_threshold": 5,
    "lockout_duration_minutes": 30,
}

# ============================================================================
# ACCOUNT THRESHOLDS
# ============================================================================
# Number of days of inactivity before flagging accounts for review

INACTIVE_THRESHOLD_DAYS = 90

# ============================================================================
# OUTPUT PATHS
# ============================================================================
# Directory paths for generated reports and log files

REPORT_OUTPUT_DIR = "reports"

# ============================================================================
# LOGGING CONFIGURATION
# ============================================================================
# Logging level and file path

LOG_LEVEL = "INFO"
LOG_FILE = "logs/ad_automation.log"
