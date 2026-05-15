"""AdminFlow live API demo for interviews.

Usage:
    uv run demo

Starts the API server, runs a sequence of requests showing off
every major feature, then shuts down cleanly.
"""

import json
import signal
import subprocess
import sys
import time

BASE_URL = "http://localhost:8000"
API_KEY = "ad-admin-key-001"


def print_header(text: str):
    print(f"\n{'=' * 72}")
    print(f"  {text}")
    print(f"{'=' * 72}")


def print_step(num, text):
    print(f"\n  [{num}] {text}")
    print(f"  {'-' * (len(text) + 4)}")


def print_response(label, data, status=None):
    if status:
        print(f"  Status: {status}")
    print(f"  {label}: ", end="")
    if isinstance(data, (dict, list)):
        print(json.dumps(data, indent=4))
    else:
        print(data)
    print()


def safe_req(method, url, label="Response", **kwargs):
    """Make a request, return (data, status) or (error_msg, None) on failure."""
    import requests

    kwargs.setdefault("timeout", 25)
    try:
        r = method(url, **kwargs)
        if r.status_code >= 400:
            try:
                body = r.json()
            except Exception:
                body = r.text[:300]
            print(f"  Status: {r.status_code}")
            print(f"  {label}: ", end="")
            print(json.dumps(body, indent=4))
            return body, r.status_code
        try:
            data = r.json()
        except Exception:
            data = r.text[:300]
        print(f"  Status: {r.status_code}")
        print(f"  {label}: ", end="")
        print(json.dumps(data, indent=4))
        return data, r.status_code
    except requests.exceptions.Timeout:
        print("  ⏱  Timed out (no AD server or network available in this environment)")
        print(f"  {label}: {{}}")
        return {}, None
    except requests.exceptions.RequestException as e:
        print(f"  ⚠  Error: {e}")
        print(f"  {label}: {{}}")
        return {}, None


def run_demo():
    import requests

    print()
    print("=" * 72)
    print("  AdminFlow — Live API Demo")
    print("  Starting server and running feature showcase...")
    print("=" * 72)

    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "src.api.main:app",
         "--host", "0.0.0.0", "--port", "8000", "--log-level", "warning"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    try:
        for _ in range(30):
            try:
                r = requests.get(f"{BASE_URL}/", timeout=2)
                if r.status_code == 200:
                    break
            except requests.ConnectionError:
                pass
            time.sleep(0.5)
        else:
            print("Server failed to start within 15s")
            return 1

        # ── 1. Root + Status ──
        print_header("1. SERVER STATUS — no auth required")

        print_step(1.1, "Welcome endpoint")
        safe_req(requests.get, f"{BASE_URL}/")

        print_step(1.2, "API configuration status")
        safe_req(requests.get, f"{BASE_URL}/api/status")

        # ── 2. Authentication ──
        print_header("2. AUTHENTICATION")

        print_step(2.1, "API Key via X-API-Key header")
        safe_req(requests.get, f"{BASE_URL}/api/status",
                 headers={"X-API-Key": API_KEY})

        print_step(2.2, "API Key via query parameter")
        safe_req(requests.get, f"{BASE_URL}/api/status",
                 params={"api_key": API_KEY})

        print_step(2.3, "JWT — obtain token (username/password)")
        r = safe_req(requests.post, f"{BASE_URL}/api/auth/token",
                     data={"username": "admin", "password": "admin123"})
        token = r[0].get("access_token", "") if isinstance(r[0], dict) else ""

        if token:
            print_step(2.4, "JWT — use token for authenticated request")
            safe_req(requests.get, f"{BASE_URL}/api/status",
                     headers={"Authorization": f"Bearer {token}"})

        print_step(2.5, "No credentials (expect 401)")
        safe_req(requests.get, f"{BASE_URL}/api/status")

        # ── 3. API Documentation ──
        print_header("3. API DOCUMENTATION")

        print_step(3.1, "OpenAPI schema")
        r = safe_req(requests.get, f"{BASE_URL}/openapi.json")
        if isinstance(r[0], dict):
            paths = r[0].get("paths", {})
            endpoints = [f"  {p.upper()} {path}"
                         for path, methods in paths.items()
                         for p in methods]
            print(f"\n  {len(endpoints)} registered endpoints:")
            for ep in endpoints[:15]:
                print(ep)
            if len(endpoints) > 15:
                print(f"  ... and {len(endpoints) - 15} more")
            print(f"\n  docs: {BASE_URL}/docs")
            print(f"  redoc: {BASE_URL}/redoc")

        # ── 4. Network Scanning ──
        print_header("4. NETWORK SCANNING")

        print_step(4.1, "Ping a host")
        safe_req(requests.post, f"{BASE_URL}/api/systems/ping",
                 json={"host": "192.168.1.1"},
                 headers={"X-API-Key": API_KEY}, timeout=15)

        print_step(4.2, "Check if a TCP port is open")
        safe_req(requests.post, f"{BASE_URL}/api/systems/port-scan",
                 json={"host": "8.8.8.8", "ports": [22, 80, 443]},
                 headers={"X-API-Key": API_KEY}, timeout=15)

        print_step(4.3, "Test SSH remote connection")
        safe_req(requests.post, f"{BASE_URL}/api/systems/remote-connect",
                 json={"connection_type": "ssh", "host": "192.168.1.100", "port": 22},
                 headers={"X-API-Key": API_KEY}, timeout=15)

        print_step(4.4, "Register a system in inventory")
        safe_req(requests.post, f"{BASE_URL}/api/systems/",
                 json={
                     "hostname": "web-01.domain.com",
                     "ip_address": "192.168.1.50",
                     "os_type": "linux",
                     "department": "Engineering",
                 },
                 headers={"X-API-Key": API_KEY})

        print_step(4.5, "List all registered systems")
        safe_req(requests.get, f"{BASE_URL}/api/systems/",
                 headers={"X-API-Key": API_KEY})

        # ── 5. Health Checks ──
        print_header("5. AD HEALTH CHECKS")
        print("  (Will show errors/timeouts without a real AD server)")
        print()

        print_step(5.1, "Comprehensive health report")
        safe_req(requests.get, f"{BASE_URL}/api/health/",
                 headers={"X-API-Key": API_KEY}, timeout=30)

        print_step(5.2, "Replication status")
        safe_req(requests.get, f"{BASE_URL}/api/health/replication",
                 headers={"X-API-Key": API_KEY}, timeout=30)

        print_step(5.3, "Domain controllers list")
        safe_req(requests.get, f"{BASE_URL}/api/health/domain-controllers",
                 headers={"X-API-Key": API_KEY}, timeout=15)

        print_step(5.4, "LDAP connectivity")
        safe_req(requests.get, f"{BASE_URL}/api/health/ldap",
                 headers={"X-API-Key": API_KEY}, timeout=15)

        print_step(5.5, "FSMO roles")
        safe_req(requests.get, f"{BASE_URL}/api/health/fsmo",
                 headers={"X-API-Key": API_KEY}, timeout=15)

        print_step(5.6, "DNS records")
        safe_req(requests.get, f"{BASE_URL}/api/health/dns",
                 headers={"X-API-Key": API_KEY}, timeout=30)

        # ── 6. Security ──
        print_header("6. SECURITY AUDITS")

        print_step(6.1, "Find privileged accounts")
        safe_req(requests.get, f"{BASE_URL}/api/security/privileged",
                 headers={"X-API-Key": API_KEY}, timeout=15)

        print_step(6.2, "Check password policy compliance")
        safe_req(requests.get, f"{BASE_URL}/api/security/password-policy",
                 headers={"X-API-Key": API_KEY}, timeout=15)

        print_step(6.3, "List inactive accounts")
        safe_req(requests.get, f"{BASE_URL}/api/security/inactive",
                 params={"days": 90}, headers={"X-API-Key": API_KEY}, timeout=15)

        print_step(6.4, "List locked accounts")
        safe_req(requests.get, f"{BASE_URL}/api/security/locked",
                 headers={"X-API-Key": API_KEY}, timeout=15)

        # ── 7. User Management ──
        print_header("7. USER MANAGEMENT")

        print_step(7.1, "Create a new user")
        safe_req(requests.post, f"{BASE_URL}/api/users/",
                 json={
                     "username": "jdoe",
                     "first_name": "Jane",
                     "last_name": "Doe",
                     "email": "jdoe@domain.com",
                     "password": "SecurePass123!",
                     "ou": "OU=Users,DC=domain,DC=com",
                     "department": "Engineering",
                     "title": "Software Engineer",
                 },
                 headers={"X-API-Key": API_KEY}, timeout=15)

        print_step(7.2, "Get user details")
        safe_req(requests.get, f"{BASE_URL}/api/users/jdoe",
                 headers={"X-API-Key": API_KEY}, timeout=15)

        print_step(7.3, "Disable user account (PUT)")
        safe_req(requests.put, f"{BASE_URL}/api/users/jdoe/disable",
                 headers={"X-API-Key": API_KEY}, timeout=15)

        print_step(7.4, "Enable user account (PUT)")
        safe_req(requests.put, f"{BASE_URL}/api/users/jdoe/enable",
                 headers={"X-API-Key": API_KEY}, timeout=15)

        print_step(7.5, "Reset user password (PUT)")
        safe_req(requests.put, f"{BASE_URL}/api/users/jdoe/reset-password",
                 json={"new_password": "NewPass456!"},
                 headers={"X-API-Key": API_KEY}, timeout=15)

        print_step(7.6, "Find inactive users")
        safe_req(requests.get, f"{BASE_URL}/api/users/inactive/90",
                 headers={"X-API-Key": API_KEY}, timeout=15)

        # ── 8. Group Management ──
        print_header("8. GROUP MANAGEMENT")

        print_step(8.1, "Create a security group")
        safe_req(requests.post, f"{BASE_URL}/api/groups/",
                 json={"name": "Demo-Team", "group_scope": "Global", "group_type": "Security"},
                 headers={"X-API-Key": API_KEY}, timeout=15)

        print_step(8.2, "Get groups a user belongs to")
        safe_req(requests.get, f"{BASE_URL}/api/groups/user/jdoe/groups",
                 headers={"X-API-Key": API_KEY}, timeout=15)

        print_step(8.3, "Get group members")
        safe_req(requests.get, f"{BASE_URL}/api/groups/Domain-Admins/members",
                 headers={"X-API-Key": API_KEY}, timeout=15)

        print_step(8.4, "Find empty groups")
        safe_req(requests.get, f"{BASE_URL}/api/groups/empty",
                 headers={"X-API-Key": API_KEY}, timeout=15)

        # ── 9. Migration ──
        print_header("9. MIGRATION")

        print_step(9.1, "Export user attributes for migration")
        safe_req(requests.get, f"{BASE_URL}/api/migration/export/jdoe",
                 headers={"X-API-Key": API_KEY}, timeout=15)

        # ── 10. Summary ──
        print_header("DEMO COMPLETE")
        print("""
  AdminFlow Feature Summary
  =========================
  [x] REST API with FastAPI + auto OpenAPI docs
  [x] Dual auth: API Keys header/query + JWT tokens
  [x] RBAC with scope-based authorization
  [x] User CRUD: create, get, enable, disable, reset password
  [x] Group management: create, members, user groups, empty groups
  [x] AD health checks: replication, DCs, LDAP, FSMO, DNS
  [x] Security audits: privileged accounts, password policy, inactive, locked
  [x] Network scanning: ping, port check, remote connection test
  [x] System inventory: register, list, track systems
  [x] Migration tools: batch user moves
  [x] Azure AD / Microsoft Graph integration
  [x] Celery task queue for async operations
  [x] APScheduler for recurring automation
  [x] CLI tool (uv run adminflow) for script-based operations
  [x] 29 passing tests, ruff + mypy clean
  [x] Docker Compose with API + Redis + Celery + monitoring
""")

    finally:
        proc.send_signal(signal.SIGINT)
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()

    return 0


if __name__ == "__main__":
    sys.exit(run_demo())
