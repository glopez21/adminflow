# AdminFlow

<div align="center">

**Automate. Monitor. Secure.**

A comprehensive Python-based automation platform for Microsoft Active Directory management with REST API, web dashboard, and remote system connectivity.

[![Python](https://img.shields.io/badge/Python-3.9+-3776AB?style=flat&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Flask](https://img.shields.io/badge/Flask-000000?style=flat&logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Status](https://img.shields.io/badge/Status-Active-success.svg)](https://github.com/yourusername/adminflow)

</div>

---

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [API Reference](#api-reference)
- [Web Dashboard](#web-dashboard)
- [CLI Usage](#cli-usage)
- [Azure AD Integration](#azure-ad-integration)
- [Scheduled Jobs](#scheduled-jobs)
- [Security](#security)
- [Contributing](#contributing)
- [License](#license)

---

## Overview

**AdminFlow** is a production-ready IT automation platform designed for Windows Active Directory management. It provides a unified interface for managing users, groups, security audits, and remote system connectivity through both REST API and web dashboard.

### Use Cases

- **Identity & Access Management**: Create, modify, and disable AD user accounts
- **Security Auditing**: Identify privileged, inactive, and locked accounts
- **System Inventory**: Track and manage remote systems across your infrastructure
- **Automation**: Schedule recurring tasks and automated workflows
- **Cloud Integration**: Sync with Azure AD / Microsoft Graph
- **Remote Access**: Test SSH, RDP, WinRM, VNC, and SMB connections

---

## Features

### Core Capabilities

| Feature | Description |
|---------|-------------|
| **User Management** | Create, disable, enable, move AD users; reset passwords |
| **Group Management** | Create groups, manage membership, audit group assignments |
| **Health Monitoring** | DC connectivity, replication status, FSMO roles, DNS verification |
| **Security Auditing** | Privileged accounts, password policies, locked accounts detection |
| **Network Scanning** | Port scanning, ping sweeps, service detection |
| **Remote Connections** | Test SSH, RDP, VNC, WinRM, SMB connectivity |
| **User Migration** | CSV import, batch operations, OU migrations |
| **Azure AD Sync** | Hybrid identity management via Microsoft Graph API |
| **Scheduled Jobs** | Automated daily/weekly maintenance tasks |
| **REST API** | Full programmatic access with JWT/API key auth |
| **Web Dashboard** | Visual management interface |

### Connection Types Supported

| Protocol | Port | Description | Platform Support |
|----------|------|-------------|-------------------|
| SSH | 22 | Secure Shell | Linux/macOS (native), Windows (via CLI) |
| RDP | 3389 | Remote Desktop Protocol | Windows (native) |
| VNC | 5900+ | Virtual Network Computing | Cross-platform |
| WinRM | 5985/5986 | Windows Remote Management | Windows (native) |
| SMB | 445 | Server Message Block | Windows (native), Linux (via smbclient) |
| Telnet | 23 | Unencrypted remote access | Legacy systems |

---

## Architecture

```
adminflow/
├── src/
│   ├── main.py                     # CLI entry point
│   ├── api/                        # FastAPI REST API
│   │   ├── main.py                 # Application factory
│   │   ├── middleware/
│   │   │   └── auth.py             # JWT/API key authentication
│   │   ├── models/
│   │   │   └── schemas.py          # Pydantic request/response models
│   │   └── routes/
│   │       ├── users.py            # User management endpoints
│   │       ├── groups.py           # Group management endpoints
│   │       ├── health.py           # Health check endpoints
│   │       ├── security.py         # Security audit endpoints
│   │       ├── migration.py        # Migration endpoints
│   │       └── systems.py          # Remote systems endpoints
│   ├── user_management/            # AD user automation modules
│   │   ├── ad_user_manager.py      # User CRUD operations
│   │   └── group_management.py     # Group operations
│   ├── health_checks/              # AD monitoring modules
│   │   └── ad_health.py            # Health check implementations
│   ├── security/                   # Security audit modules
│   ├── migration/                  # User migration modules
│   │   └── ad_migration.py         # CSV import, batch operations
│   └── utils/                      # Shared utilities
│       ├── ad_connection.py        # AD connection handler
│       ├── logger.py                # Logging configuration
│       ├── network.py              # Network scanning utilities
│       ├── remote_connections.py   # SSH/RDP/VNC handlers
│       ├── scheduler.py            # Job scheduling
│       └── azure_ad.py            # Azure AD integration
├── web/
│   ├── app.py                      # Flask web dashboard
│   └── templates/                  # HTML templates
├── config/
│   └── settings.py                 # Configuration management
├── tests/                          # Test suite
├── reports/                        # Generated reports
├── logs/                          # Application logs
└── pyproject.toml                 # Project configuration
```

---

## Tech Stack

| Component | Technology |
|-----------|------------|
| **Language** | Python 3.9+ |
| **API Framework** | FastAPI |
| **Web Dashboard** | Flask |
| **Database** | SQLite (system inventory) |
| **AD Libraries** | pyad, python-ldap |
| **Remote Connections** | paramiko, socket |
| **Authentication** | JWT, API Keys |
| **Azure Integration** | Microsoft Graph API (msal) |
| **Task Scheduling** | APScheduler |

---

## Quick Start

### Prerequisites

- Python 3.9 or higher
- uv package manager (recommended)

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/adminflow.git
cd adminflow

# Install uv if not already available
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create virtual environment and install dependencies
uv sync
```

### Configuration

1. Copy the example configuration:

```bash
cp config/settings.example.py config/settings.py
```

2. Edit `config/settings.py` with your AD settings:

```python
# Active Directory Configuration
AD_SERVER = "dc01.yourdomain.com"
AD_BASE_DN = "dc=yourdomain,dc=com"
AD_USER = "admin@yourdomain.com"
AD_PASSWORD = "your_password"  # Or use environment variable

# Default OU for new users
DEFAULT_OU = "ou=Users,dc=yourdomain,dc=com"

# Inactive account threshold (days)
INACTIVE_THRESHOLD_DAYS = 90
```

3. Set environment variables (recommended for production):

```bash
export AD_PASSWORD="your_actual_password"
export AZURE_TENANT_ID="your-tenant-id"
export AZURE_CLIENT_ID="your-client-id"
export AZURE_CLIENT_SECRET="your-client-secret"
```

### Running the Application

#### Option 1: REST API Server (Recommended)

```bash
# Start FastAPI server
uv run python -m src.api.main

# Server runs at http://localhost:8000
# Interactive API docs at http://localhost:8000/docs
```

#### Option 2: Web Dashboard

```bash
# Start Flask web dashboard
uv run python -m web.app

# Dashboard runs at http://localhost:5000
# Default credentials: admin / admin123
```

#### Option 3: CLI

```bash
# User management
uv run python -m src.main user create --username jsmith --first-name John --last-name Smith --email jsmith@domain.com

# Health checks
uv run python -m src.main health all

# Security audits
uv run python -m src.main security privileged
```

---

## Configuration

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `AD_SERVER` | Domain controller hostname | Yes |
| `AD_BASE_DN` | Base Distinguished Name | Yes |
| `AD_USER` | Admin username | Yes |
| `AD_PASSWORD` | Admin password | Yes |
| `AZURE_TENANT_ID` | Azure AD tenant ID | For Azure integration |
| `AZURE_CLIENT_ID` | Azure app client ID | For Azure integration |
| `AZURE_CLIENT_SECRET` | Azure app secret | For Azure integration |
| `API_SECRET_KEY` | JWT signing key | Yes (production) |

### Settings File

The `config/settings.py` file contains:

- Active Directory connection parameters
- Default OU paths
- Inactive account thresholds
- Scheduler configuration
- Logging levels

---

## API Reference

### Base URL

```
http://localhost:8000/api
```

### Authentication

#### Option 1: API Key

```bash
# Via Header
curl -H "X-API-Key: ad-admin-key-001" http://localhost:8000/api/users

# Via Query Parameter
curl "http://localhost:8000/api/users?api_key=ad-admin-key-001"
```

#### Option 2: JWT Token

```bash
# Get token
curl -X POST "http://localhost:8000/api/auth/token" \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}'

# Use token
curl -H "Authorization: Bearer <token>" http://localhost:8000/api/users
```

### Available API Keys

| Key | Access Level |
|-----|---------------|
| `ad-admin-key-001` | Full access |
| `ad-auto-key-002` | Automation access |
| `ad-read-key-003` | Read-only access |

### Endpoints Overview

#### Users

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/users` | List all AD users |
| POST | `/users` | Create new user |
| GET | `/users/{username}` | Get user details |
| PUT | `/users/{username}/disable` | Disable user account |
| PUT | `/users/{username}/enable` | Enable user account |
| PUT | `/users/{username}/reset-password` | Reset user password |
| PUT | `/users/{username}/move` | Move user to new OU |
| GET | `/users/inactive/{days}` | Find inactive users |

#### Groups

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/groups` | List all groups |
| POST | `/groups` | Create new group |
| GET | `/groups/{name}/members` | Get group members |
| POST | `/groups/add-member` | Add member to group |
| GET | `/groups/user/{username}/groups` | Get user's groups |
| GET | `/groups/empty` | Find empty groups |

#### Health

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health/` | Run all health checks |
| GET | `/health/replication` | Check AD replication |
| GET | `/health/domain-controllers` | List domain controllers |
| GET | `/health/fsmo` | Check FSMO roles |
| GET | `/health/dns` | Verify DNS records |

#### Security

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/security/` | Run all security audits |
| GET | `/security/privileged` | Find privileged accounts |
| GET | `/security/password-policy` | Check password policy |
| GET | `/security/inactive/{days}` | Find inactive accounts |
| GET | `/security/locked` | Find locked accounts |
| POST | `/security/network-scan` | Scan network range |

#### Systems

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/systems/` | List system inventory |
| POST | `/systems/` | Add system to inventory |
| GET | `/systems/{id}` | Get system details |
| PUT | `/systems/{id}` | Update system |
| DELETE | `/systems/{id}` | Remove system |
| POST | `/systems/port-scan` | Scan ports on host |
| POST | `/systems/remote-connect` | Test connection type |

#### Migration

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/migration/csv` | Import users from CSV |
| POST | `/migration/move` | Batch move users |
| GET | `/migration/export/{username}` | Export user attributes |
| POST | `/migration/group-mapping` | Set group mappings |

For complete API documentation, visit `/docs` when the server is running.

---

## Web Dashboard

The web dashboard provides a visual interface for all AdminFlow operations.

### Features

- **Dashboard**: Overview with statistics (inactive, privileged, locked accounts)
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

> **Important**: Change the default credentials in production environments.

---

## CLI Usage

### User Management

```bash
# Create user
python -m src.main user create --username jsmith --first-name John --last-name Smith --email jsmith@domain.com --department IT

# List inactive users
python -m src.main user inactive --days 90

# Disable user
python -m src.main user disable jsmith

# Reset password
python -m src.main user reset-password jsmith --new-password "NewP@ss123!"
```

### Health Checks

```bash
# Run all health checks
python -m src.main health all

# Check replication
python -m src.main health replication

# List domain controllers
python -m src.main health dc-list
```

### Security Audits

```bash
# Run all security audits
python -m src.main security all

# Find privileged accounts
python -m src.main security privileged

# Find locked accounts
python -m src.main security locked
```

### Network Operations

```bash
# Port scan
python -m src.main network scan --host 192.168.1.10 --ports 22,80,443,3389

# Ping host
python -m src.main network ping --host 192.168.1.10 --count 4
```

---

## Azure AD Integration

AdminFlow supports integration with Azure Active Directory via Microsoft Graph API.

### Configuration

```bash
export AZURE_TENANT_ID="your-tenant-id"
export AZURE_CLIENT_ID="your-client-id"
export AZURE_CLIENT_SECRET="your-client-secret"
```

### Usage

```python
from src.utils.azure_ad import create_azure_manager_from_config

# Create Azure AD manager
azure = create_azure_manager_from_config()

# List users
users = azure.list_users()

# Create user
azure.create_user(
    display_name="John Smith",
    mail="jsmith@domain.com",
    user_principal_name="jsmith@domain.onmicrosoft.com"
)

# Reset password
azure.reset_password("jsmith@domain.onmicrosoft.com", "NewP@ss123!")
```

### Supported Operations

- List users, groups, and devices
- Create, update, and delete users
- Manage group membership
- Reset passwords
- Disable devices
- Sync with on-premises AD

---

## Scheduled Jobs

The scheduler runs automated tasks at configured intervals:

| Job | Schedule | Description |
|-----|----------|-------------|
| Daily Health Check | 6:00 AM | Runs full AD health check |
| Weekly Security Audit | Sunday 2:00 AM | Generate security audit report |
| Weekly Inactive Accounts | Monday 7:00 AM | Find and report inactive accounts |
| Daily Config Backup | Every 24 hours | Backup system configuration |

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

## Security

### Production Recommendations

1. **Change Default Credentials**: Update default API keys and web dashboard credentials
2. **Environment Variables**: Use environment variables for sensitive data
3. **HTTPS**: Enable HTTPS in production (use reverse proxy)
4. **Rate Limiting**: Implement API rate limiting
5. **Logging**: Review logs regularly for suspicious activity
6. **Updates**: Keep dependencies updated
7. **Access Control**: Implement role-based access control

### Security Features

- JWT token authentication
- API key authentication
- Role-based access control
- Audit logging
- Password policy enforcement

---

## Development

### Running Tests

```bash
uv run pytest tests/
```

### Code Quality

```bash
# Linting
uv run ruff check .

# Type checking
uv run mypy src/
```

### Adding New Features

1. **Add API Endpoint**: Create route in `src/api/routes/`, register in `src/api/main.py`
2. **Add CLI Command**: Add to `src/main.py`
3. **Add Dashboard Page**: Create template in `web/templates/`, add route in `web/app.py`

---

## Troubleshooting

### AD Connection Issues

1. Verify credentials in configuration
2. Check network connectivity to domain controller
3. Ensure required libraries are installed (pyad, python-ldap)
4. Check firewall rules

### API Not Starting

```bash
# Check port availability
lsof -i :8000  # API
lsof -i :5000  # Web

# Check logs
tail -f logs/ad_automation.log
```

### Remote Connection Failures

1. Verify firewall rules
2. Check target reachability (ping test)
3. Verify service is running on target
4. Confirm credentials if required

---

## Contributing

Contributions are welcome! Please read our contributing guidelines before submitting pull requests.

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## Support

- Documentation: [docs/](docs/)
- Issue Tracker: [GitHub Issues](https://github.com/yourusername/adminflow/issues)
- Discussions: [GitHub Discussions](https://github.com/yourusername/adminflow/discussions)

---

<div align="center">

**AdminFlow** - *Automate. Monitor. Secure.*

</div>