# AdminFlow

**Automate. Monitor. Secure.**

Python-based automation system for managing Microsoft Active Directory environments with REST API, web dashboard, and remote system connections.

## Project Overview

**AdminFlow** is a comprehensive IT automation platform for Windows Active Directory management.

**Tagline**: *"Automate. Monitor. Secure."*

### Core Features

- Active Directory user, group, and security management
- REST API for programmatic access
- Web dashboard UI for visual management
- Remote system connections (SSH, RDP, VNC, WinRM, SMB)
- Scheduled automation jobs
- Azure AD / Microsoft Graph integration
- Network scanning and system inventory

## Tech Stack

- **Language**: Python 3.9+
- **API Framework**: FastAPI
- **Web Dashboard**: Flask + HTML/CSS/JS
- **AD Libraries**: pyad, python-ldap
- **Remote Connections**: paramiko, socket
- **Database**: SQLite
- **Auth**: JWT / API Keys

## Project Structure

```
ad-automation-system/
├── src/
│   ├── main.py                     # CLI entry point
│   ├── api/
│   │   ├── main.py                 # FastAPI application
│   │   ├── middleware/
│   │   │   └── auth.py             # JWT/API key authentication
│   │   ├── models/
│   │   │   └── schemas.py          # Pydantic models
│   │   └── routes/
│   │       ├── users.py            # User endpoints
│   │       ├── groups.py           # Group endpoints
│   │       ├── health.py           # Health check endpoints
│   │       ├── security.py         # Security audit endpoints
│   │       ├── migration.py        # Migration endpoints
│   │       └── systems.py          # Remote systems endpoints
│   ├── user_management/            # AD user automation
│   ├── health_checks/              # AD monitoring
│   ├── security/                   # Security audits
│   ├── migration/                  # User migration
│   └── utils/
│       ├── ad_connection.py         # AD connection handler
│       ├── logger.py                # Logging utilities
│       ├── network.py              # Network scanning
│       ├── remote_connections.py   # SSH/RDP/VNC handlers
│       ├── scheduler.py            # Automation jobs
│       └── azure_ad.py             # Azure AD integration
├── web/
│   ├── app.py                      # Flask dashboard
│   └── templates/                  # HTML templates
├── config/
│   └── settings.py                 # Configuration
├── reports/                        # Generated reports
├── logs/                          # Execution logs
└── README.md
```

## Installation

```bash
cd /home/w01f/projects/ad-automation-system

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/macOS
# venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt
```

## Configuration

Edit `config/settings.py`:

```python
# Active Directory Connection
AD_SERVER = "dc01.yourdomain.com"
AD_BASE_DN = "dc=yourdomain,dc=com"
AD_USER = "admin@yourdomain.com"
AD_PASSWORD = "your_password"  # Or use environment variable

# Default OU for new users
DEFAULT_OU = "ou=Users,dc=yourdomain,dc=com"

# Inactive account threshold (days)
INACTIVE_THRESHOLD_DAYS = 90
```

### Environment Variables (Recommended)

```bash
export AD_PASSWORD="your_actual_password"
export AZURE_TENANT_ID="your-tenant-id"
export AZURE_CLIENT_ID="your-client-id"
export AZURE_CLIENT_SECRET="your-client-secret"
```

---

## Running the Application

### Option 1: REST API Server (Recommended)

```bash
# Start FastAPI server
python -m src.api.main

# Server runs at http://localhost:8000
# Interactive API docs at http://localhost:8000/docs
```

### Option 2: Web Dashboard

```bash
# Start Flask web dashboard
python -m web.app

# Dashboard runs at http://localhost:5000
# Default login: admin / admin123
```

### Option 3: CLI

```bash
# User management
python -m src.main user create --username jsmith --first-name John --last-name Smith --email jsmith@domain.com
python -m src.main user inactive --days 90

# Health checks
python -m src.main health all
python -m src.main health replication

# Security audits
python -m src.main security all
python -m src.main security privileged
```

---

## API Usage Guide

### Base URL
```
http://localhost:8000/api
```

### Authentication

**Option 1: API Key**
```bash
# Header
curl -H "X-API-Key: ad-admin-key-001" http://localhost:8000/api/users

# Query parameter
curl "http://localhost:8000/api/users?api_key=ad-admin-key-001"
```

**Option 2: JWT Token**
```bash
# Get token
curl -X POST "http://localhost:8000/api/auth/token" \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}'

# Use token
curl -H "Authorization: Bearer <token>" http://localhost:8000/api/users
```

**Available API Keys:**
- `ad-admin-key-001` - Full access
- `ad-auto-key-002` - Automation access
- `ad-read-key-003` - Read-only access

### API Endpoints

#### Users

```bash
# List users (requires AD connection)
GET /api/users

# Create user
POST /api/users
{
  "username": "jsmith",
  "first_name": "John",
  "last_name": "Smith",
  "email": "jsmith@domain.com",
  "password": "P@ssw0rd123!",
  "department": "IT",
  "title": "Support Specialist"
}

# Get user info
GET /api/users/{username}

# Disable user
PUT /api/users/{username}/disable

# Enable user
PUT /api/users/{username}/enable

# Reset password
PUT /api/users/{username}/reset-password
{
  "new_password": "NewP@ss123!"
}

# Move user to new OU
PUT /api/users/{username}/move
{
  "new_ou": "ou=Disabled,dc=domain,dc=com"
}

# Get inactive users
GET /api/users/inactive/90
```

#### Groups

```bash
# List groups
GET /api/groups

# Create group
POST /api/groups
{
  "name": "IT-Developers",
  "group_scope": "Global",
  "group_type": "Security",
  "ou": "ou=Groups,dc=domain,dc=com"
}

# Get group members
GET /api/groups/{group_name}/members

# Add member
POST /api/groups/add-member
{
  "group_name": "IT-Developers",
  "member_dn": "CN=John Smith,OU=Users,dc=domain,dc=com"
}

# Get user's groups
GET /api/groups/user/{username}/groups

# Find empty groups
GET /api/groups/empty
```

#### Health Checks

```bash
# Run all health checks
GET /api/health/

# Check replication
GET /api/health/replication

# List domain controllers
GET /api/health/domain-controllers

# Test LDAP connectivity
GET /api/health/ldap?server=dc01.domain.com

# Check FSMO roles
GET /api/health/fsmo

# Verify DNS records
GET /api/health/dns
```

#### Security

```bash
# Run all security audits
GET /api/security/

# Find privileged accounts
GET /api/security/privileged

# Check password policy
GET /api/security/password-policy

# Find inactive accounts
GET /api/security/inactive/90

# Find locked accounts
GET /api/security/locked

# Audit security groups
GET /api/security/groups
```

#### Remote Connections / Systems

```bash
# Add system to inventory
POST /api/systems/
{
  "hostname": "web-server-01",
  "ip_address": "192.168.1.100",
  "system_type": "linux",
  "os": "Ubuntu 22.04",
  "location": "Data Center A",
  "tags": ["web", "production"]
}

# List systems (with filters)
GET /api/systems/?system_type=windows&status=active

# Get system details
GET /api/systems/1

# Update system
PUT /api/systems/1
{
  "status": "maintenance",
  "tags": ["web", "staging"]
}

# Delete system
DELETE /api/systems/1

# Test remote connection
POST /api/systems/remote-connect
{
  "target_host": "192.168.1.10",
  "connection_type": "ssh"
}

# Ping host
POST /api/systems/ping
{
  "host": "192.168.1.10",
  "count": 4
}

# Port scan
POST /api/systems/port-scan
{
  "host": "192.168.1.10",
  "ports": [22, 80, 443, 3389, 445]
}
```

#### Network Scanning

```bash
# Network scan
POST /api/security/network-scan
{
  "network_range": "192.168.1.0/24",
  "scan_types": ["ping", "port"],
  "ports": [22, 80, 445, 3389]
}

# Health check on target
POST /api/security/health-check
{
  "target": "192.168.1.10",
  "check_type": "port",
  "port": 22,
  "timeout": 10
}
```

#### Migration

```bash
# Migrate users from CSV
POST /api/migration/csv
Content-Type: multipart/form-data
File: users.csv (columns: username, first_name, last_name, email, password, department, title, ou, groups)

# Batch move users
POST /api/migration/move
{
  "users": ["jsmith", "jdoe"],
  "target_ou": "ou=Migrated,dc=domain,dc=com"
}

# Export user attributes
GET /api/migration/export/jsmith

# Set group mappings
POST /api/migration/group-mapping
{
  "Domain Users": "All Users",
  "Domain Admins": "Admin Group"
}
```

---

## Connection Types Supported

| Type | Port | Description | Windows | Linux | Notes |
|------|------|-------------|---------|-------|-------|
| SSH | 22 | Secure Shell | Via CLI | Native | Use paramiko for execution |
| RDP | 3389 | Remote Desktop | Native | - | Uses mstsc on Windows |
| VNC | 5900 | Virtual Network Computing | Via VNC viewer | Via VNC viewer | Cross-platform |
| WinRM | 5985 | Windows Remote Management | Native | - | HTTP/HTTPS |
| SMB | 445 | Server Message Block | Native | Via smbclient | File sharing |
| Telnet | 23 | Telnet | Via CLI | Native | Not encrypted |

### Remote Connection Example

```bash
# Test SSH connection
curl -X POST "http://localhost:8000/api/systems/remote-connect" \
  -H "Content-Type: application/json" \
  -d '{"target_host": "192.168.1.100", "connection_type": "ssh"}'

# Response
{
  "target": "192.168.1.100",
  "type": "ssh",
  "status": "success",
  "message": "SSH port is open",
  "details": {"port": 22}
}

# Test RDP
curl -X POST "http://localhost:8000/api/systems/remote-connect" \
  -H "Content-Type: application/json" \
  -d '{"target_host": "192.168.1.50", "connection_type": "rdp"}'

# Test multiple ports
curl -X POST "http://localhost:8000/api/systems/port-scan" \
  -H "Content-Type: application/json" \
  -d '{"host": "192.168.1.10", "ports": [22, 80, 443, 3389, 445, 5985]}'

# Response
{
  "host": "192.168.1.10",
  "ports": [
    {"host": "192.168.1.10", "port": 22, "status": "open", "service": "SSH"},
    {"host": "192.168.1.10", "port": 80, "status": "open", "service": "HTTP"},
    {"host": "192.168.1.10", "port": 443, "status": "open", "service": "HTTPS"},
    {"host": "192.168.1.10", "port": 3389, "status": "closed", "service": "RDP"},
    {"host": "192.168.1.10", "port": 445, "status": "open", "service": "SMB"},
    {"host": "192.168.1.10", "port": 5985, "status": "closed", "service": "WinRM"}
  ]
}
```

---

## Web Dashboard

The dashboard provides a visual interface for:

- **Dashboard**: Overview with stats (inactive, privileged, locked accounts)
- **Users**: Create and manage AD users
- **Groups**: View and manage group membership
- **Health**: Run AD health checks
- **Security**: Run security audits
- **Remote Connect**: Test remote connections and port scanning
- **Systems**: View system inventory
- **Jobs**: View scheduled automation jobs
- **Settings**: Configure system settings

### Access

```
URL: http://localhost:5000
Username: admin
Password: admin123
```

---

## Scheduled Jobs

The scheduler runs automated tasks at configured intervals:

- **Daily Health Check** (6:00 AM) - Runs full AD health check
- **Weekly Security Audit** (Sunday 2:00 AM) - Security audit report
- **Weekly Inactive Accounts** (Monday 7:00 AM) - Find inactive accounts
- **Daily Config Backup** (Every 24 hours) - Backup configuration

### Manage Jobs via API

```bash
# Get all jobs
GET /api/jobs

# Run specific job manually
POST /api/jobs/{job_name}/run

# Get next scheduled runs
GET /api/jobs/next-runs
```

---

## Azure AD Integration

Configure Azure AD for hybrid/ cloud management:

```bash
# Set environment variables
export AZURE_TENANT_ID="your-tenant-id"
export AZURE_CLIENT_ID="your-client-id"
export AZURE_CLIENT_SECRET="your-client-secret"
```

Then use the Azure manager:

```python
from src.utils.azure_ad import create_azure_manager_from_config

azure = create_azure_manager_from_config()
users = azure.list_users()
```

### Azure AD Operations

- List users, groups, devices
- Create/update/delete users
- Reset passwords
- Manage group membership
- Disable devices
- Sync with on-prem AD

---

## Reports

Reports are generated in `reports/` directory:

- `health_report_YYYYMMDD.json` - Daily health reports
- `security_audit_YYYYMMDD.json` - Security audit reports
- `inactive_accounts_YYYYMMDD.json` - Inactive account lists
- `config_backup_*.tar.gz` - Configuration backups

---

## Troubleshooting

### AD Connection Issues

1. Verify credentials in `config/settings.py`
2. Check network connectivity to DC
3. Ensure pyad/pywin32 installed (Windows)
4. For Linux: verify python-ldap and LDAP access

### API Not Starting

```bash
# Check port availability
lsof -i :8000  # API
lsof -i :5000  # Web

# Check logs
tail -f logs/ad_automation.log
```

### Remote Connection Failures

1. Check firewall rules
2. Verify target is reachable (ping test)
3. Check service is running on target
4. Verify credentials if required

---

## Development

### Run Tests

```bash
pytest tests/
```

### Add New API Endpoint

1. Create route in `src/api/routes/`
2. Register in `src/api/main.py`
3. Add to this README

### Add New Dashboard Page

1. Create template in `web/templates/`
2. Add route in `web/app.py`

---

## Security Notes

- Change default API keys in `src/api/middleware/auth.py`
- Change default web credentials in `web/app.py`
- Use environment variables for passwords
- Enable HTTPS in production
- Implement rate limiting
- Regular security audits

---

## License

MIT