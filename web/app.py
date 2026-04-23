"""
Web Dashboard for AdminFlow AD Automation System.

This module provides a Flask-based web dashboard for managing and monitoring
Active Directory through a browser interface. It includes authentication,
AD user/group management, health checks, security auditing, remote
connectivity testing, and scheduled job management.

Features:
    - User authentication with Flask-Login
    - Dashboard with security statistics
    - User management (create, list)
    - Group management
    - AD health monitoring
    - Security auditing
    - System inventory and remote connections
    - Scheduled jobs management

Routes:
    / - Dashboard index (login required)
    /login - Authentication page
    /logout - Logout and redirect
    /dashboard - Main dashboard with statistics
    /users - User management interface
    /groups - Group management interface
    /health - AD health check interface
    /security - Security audit interface
    /systems - System inventory interface
    /remote - Remote connection testing interface
    /jobs - Scheduled jobs interface
    /settings - Application settings interface

API Routes:
    /api/dashboard/stats - Dashboard statistics
    /api/users/list - List users
    /api/users/create - Create new user
    /api/groups/list - List groups
    /api/health/check - Run health check
    /api/security/audit - Run security audit
    /api/remote/connect - Test remote connection

Usage:
    python web/app.py

    Or via Flask CLI:
    flask --app web.app run --host 0.0.0.0 --port 5000

Security Warning:
    The default secret key and user credentials must be changed
    in production. Use environment variables for sensitive settings.
"""

import logging
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from flask import Flask, flash, jsonify, redirect, render_template, request, url_for
from flask_login import (
    LoginManager,
    UserMixin,
    current_user,
    login_required,
    login_user,
    logout_user,
)
from werkzeug.security import check_password_hash, generate_password_hash

import config.settings as settings
from src.health_checks.ad_health import ADHealthChecker
from src.security.ad_security import ADSecurityAuditor
from src.user_management.ad_user_manager import ADUserManager
from src.utils.ad_connection import ADConnection

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================================
# FLASK APPLICATION CONFIGURATION
# ============================================================================

app = Flask(__name__)
# WARNING: Change this secret key in production!
# Use environment variable: os.environ.get("FLASK_SECRET_KEY")
app.secret_key = "change-this-secret-key-in-production"

# ============================================================================
# FLASK-LOGIN CONFIGURATION
# ============================================================================

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"


class User(UserMixin):
    """
    Flask-Login user model.

    Represents an authenticated user in the web dashboard.
    Stores user ID, username, and role for authorization.

    Attributes:
        id: Unique user identifier
        username: User's display name
        role: User role for authorization (admin, viewer)
    """

    def __init__(self, user_id, username, role="admin"):
        self.id = user_id
        self.username = username
        self.role = role


# Mock user database for demonstration
# WARNING: Replace with proper database and strong passwords in production
USERS = {
    "admin": {"password": generate_password_hash("admin123"), "role": "admin"},
    "viewer": {"password": generate_password_hash("viewer123"), "role": "viewer"},
}


@login_manager.user_loader
def load_user(user_id):
    """
    Load a user from the mock database by ID.

    Called by Flask-Login to retrieve user objects for session management.

    Args:
        user_id: The user ID to look up

    Returns:
        User object if found, None otherwise
    """
    for username, data in USERS.items():
        if username == user_id:
            return User(user_id, username, data["role"])
    return None


def get_ad_connection():
    """
    Create and establish an Active Directory connection.

    Uses settings from config/settings.py to configure the connection.

    Returns:
        ADConnection: Connected AD connection instance

    Note:
        Caller is responsible for calling conn.disconnect() when done
    """
    conn = ADConnection(
        server=settings.AD_SERVER,
        username=settings.AD_USER,
        password=settings.AD_PASSWORD,
        base_dn=settings.AD_BASE_DN,
    )
    conn.connect()
    return conn


# ============================================================================
# PAGE ROUTES
# ============================================================================


@app.route("/")
@login_required
def index():
    """Root page - redirects to dashboard for authenticated users."""
    return render_template("index.html", user=current_user)


@app.route("/login", methods=["GET", "POST"])
def login():
    """
    Login page - handles user authentication.

    GET: Display login form
    POST: Authenticate user credentials and redirect to dashboard

    Uses Flask-Login for session management.
    """
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        if username in USERS:
            if check_password_hash(USERS[username]["password"], password):
                user = User(username, username, USERS[username]["role"])
                login_user(user)
                return redirect(url_for("index"))

        flash("Invalid credentials", "error")

    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    """Logout and redirect to login page."""
    logout_user()
    return redirect(url_for("login"))


@app.route("/dashboard")
@login_required
def dashboard():
    """Dashboard page with system overview."""
    return render_template("dashboard.html", user=current_user)


@app.route("/users")
@login_required
def users():
    """User management page."""
    return render_template("users.html", user=current_user)


@app.route("/api/dashboard/stats")
@login_required
def dashboard_stats():
    """
    API endpoint for dashboard statistics.

    Returns aggregated security statistics including:
    - Number of inactive accounts
    - Number of privileged accounts
    - Number of locked accounts

    Returns:
        JSON: Dashboard statistics dictionary
    """
    try:
        conn = get_ad_connection()
        user_mgr = ADUserManager(conn)
        auditor = ADSecurityAuditor(conn)

        inactive = user_mgr.find_inactive_users(90)
        privileged = auditor.find_privileged_accounts()
        locked = auditor.find_locked_accounts()

        conn.disconnect()

        return jsonify(
            {
                "inactive_accounts": len(inactive),
                "privileged_accounts": len(privileged),
                "locked_accounts": len(locked),
            }
        )
    except Exception as e:
        logger.error(f"Dashboard stats error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/users/list")
@login_required
def list_users():
    """
    API endpoint to list AD users.

    Returns user list from Active Directory.
    Requires AD connection to be functional.

    Returns:
        JSON: List of users or error message
    """
    try:
        conn = get_ad_connection()
        conn.disconnect()
        return jsonify({"users": [], "message": "Connect to AD to list users"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/users/create", methods=["POST"])
@login_required
def create_user():
    """
    API endpoint to create a new AD user.

    Accepts JSON body with user details and creates the account
    in Active Directory.

    Expected JSON Body:
        username, first_name, last_name, email, password,
        ou (optional), department (optional), title (optional)

    Returns:
        JSON: Creation result or error message
    """
    data = request.json

    try:
        conn = get_ad_connection()
        user_mgr = ADUserManager(conn)

        result = user_mgr.create_user(
            username=data.get("username"),
            first_name=data.get("first_name"),
            last_name=data.get("last_name"),
            email=data.get("email"),
            password=data.get("password", "ChangeMe123!"),
            ou=data.get("ou", settings.DEFAULT_OU),
            department=data.get("department"),
            title=data.get("title"),
        )

        conn.disconnect()
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/groups")
@login_required
def groups():
    """Group management page."""
    return render_template("groups.html", user=current_user)


@app.route("/api/groups/list")
@login_required
def list_groups():
    """
    API endpoint to list AD groups.

    Returns group list from Active Directory.

    Returns:
        JSON: List of groups or error message
    """
    return jsonify({"groups": [], "message": "Connect to AD to list groups"})


@app.route("/health")
@login_required
def health():
    """AD health check page."""
    return render_template("health.html", user=current_user)


@app.route("/api/health/check")
@login_required
def health_check():
    """
    API endpoint for AD health check.

    Runs comprehensive AD health check and returns results.

    Returns:
        JSON: Health check report or error message
    """
    try:
        conn = get_ad_connection()
        checker = ADHealthChecker(conn)
        result = checker.generate_health_report()
        conn.disconnect()
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/security")
@login_required
def security():
    """Security audit page."""
    return render_template("security.html", user=current_user)


@app.route("/api/security/audit")
@login_required
def security_audit():
    """
    API endpoint for security audit.

    Runs comprehensive security audit and returns results including
    privileged accounts, password policy, inactive and locked accounts.

    Returns:
        JSON: Security audit report or error message
    """
    try:
        conn = get_ad_connection()
        auditor = ADSecurityAuditor(conn)
        result = auditor.generate_security_report()
        conn.disconnect()
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/systems")
@login_required
def systems():
    """System inventory page."""
    return render_template("systems.html", user=current_user)


@app.route("/remote")
@login_required
def remote():
    """Remote connection testing page."""
    return render_template("remote.html", user=current_user)


@app.route("/api/remote/connect", methods=["POST"])
@login_required
def remote_connect():
    """
    API endpoint to test remote connectivity.

    Tests connectivity to a remote system using the specified
    connection type (SSH, RDP, VNC, WinRM, SMB).

    Expected JSON Body:
        target: Hostname or IP address
        type: Connection type (ssh, rdp, vnc, winrm, smb)

    Returns:
        JSON: Connection test result
    """
    data = request.json
    target = data.get("target")
    conn_type = data.get("type")

    from src.utils.remote_connections import ConnectionFactory

    try:
        result = ConnectionFactory.test_connection(
            connection_type=conn_type, host=target
        )
        return jsonify(
            {
                "success": result.success,
                "message": result.message,
                "details": result.details,
            }
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/jobs")
@login_required
def jobs():
    """Scheduled jobs management page."""
    return render_template("jobs.html", user=current_user)


@app.route("/settings")
@login_required
def app_settings():
    """Application settings page."""
    return render_template("settings.html", user=current_user)


@app.errorhandler(404)
def not_found(e):
    """Custom 404 error handler."""
    return render_template("404.html"), 404


# ============================================================================
# APPLICATION ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
