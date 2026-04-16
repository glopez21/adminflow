# AdminFlow Development Document

## Project Overview

AdminFlow is a Python-based automation platform for managing Microsoft Active Directory environments. It provides three interfaces — CLI, REST API (FastAPI), and a web dashboard (Flask) — for user/group management, health monitoring, security auditing, migration, remote connectivity, and Azure AD synchronization.

---

## Initial Work

### Architecture

The project follows a layered architecture:

| Layer | Components |
|-------|------------|
| Presentation | CLI (`src/main.py`), REST API (`src/api/`), Web Dashboard (`web/app.py`) |
| Business Logic | User management, group management, health checks, security audits, migration |
| Data Access | `src/utils/ad_connection.py` — single AD connection class using pyad (Windows-only) |
| Utilities | Logging, scheduling, networking, remote connections, Azure AD integration |
| Configuration | `config/settings.py` — centralized settings with placeholder defaults |
| Storage | Local JSON files (no database), file-based reports |

### Core Modules

- **ad_connection.py** — AD connection lifecycle (connect/disconnect/test) via pyad with graceful fallback
- **ad_user_manager.py** — CRUD operations for AD users, bulk creation, inactive user detection
- **group_management.py** — Group creation, membership management, empty group detection
- **ad_health.py** — DC enumeration, replication checks, LDAP connectivity, FSMO role auditing, DNS record validation
- **ad_security.py** — Privileged account discovery, password policy compliance, inactive/locked account detection
- **ad_migration.py** — CSV-based bulk user import, batch OU moves, group mapping, attribute preservation
- **azure_ad.py** — Microsoft Graph API integration for Azure AD user/group/device management, hybrid sync
- **remote_connections.py** — SSH, RDP, VNC, WinRM, SMB handlers via paramiko and subprocess
- **network.py** — Network scanning, port checking, OS fingerprinting, reverse DNS lookups
- **scheduler.py** — APScheduler-based job system for recurring health checks, security audits, and config backups

### Web Dashboard

Flask-based UI with 12 templates (login, dashboard, users, groups, health, security, systems, remote, jobs, settings). Dark sidebar theme with inline CSS, no external JavaScript or CSS frameworks.

### API

FastAPI application with 6 route groups (users, groups, health, security, migration, systems). JWT and API key authentication with role-based access control. Pydantic models for request/response validation.

---

## Current Developments

### Cross-Platform Compatibility

The codebase was originally designed for Windows, relying on `pyad` (which requires `pywin32`). Through this session, the following changes were made:

1. **Replaced `python-ldap` with `ldap3`** — `python-ldap` requires C compilation (OpenLDAP libraries) and fails on Windows. `ldap3` is a pure-Python LDAP library that works on all platforms.

2. **Fixed pyad import guard** — `pyad` raises a generic `Exception` (not `ImportError`) when `pywin32` is missing, which bypassed the original `try/except ImportError`. Changed to `except Exception` to catch this gracefully.

3. **Added missing `__init__.py` files** — 9 package directories were missing `__init__.py`, preventing proper module resolution for the `adminflow` CLI entry point.

4. **Fixed `pyproject.toml` deprecation** — Replaced `[project.optional-dependencies]` and `tool.uv.dev-dependencies` with `[dependency-groups]` to resolve the `uv` warning.

### Dependency Changes

| Package | Before | After |
|---------|--------|-------|
| python-ldap | >=3.4.0 | removed |
| ldap3 | — | >=2.9.0 |
| dev dependencies | `[project.optional-dependencies]` | `[dependency-groups]` |

---

## Issues Being Addressed

### Platform Lock-In

The system is heavily dependent on Windows-only tools:

- **pyad/pywin32** — All core AD operations (user creation, group management, health checks) use `pyad`, which only works on Windows with `pywin32` installed. On Linux/macOS, all operations return failures with warnings.
- **Windows CLI commands** — Health checks rely on `nltest`, `repadmin`, and `netdom` (Windows Server tools)
- **RDP/SMB handlers** — Use `mstsc` and `net view` (Windows-only commands)

**Current status**: The `ldap3` dependency is now available but no module yet uses it. The fallback path is a warning message and a failed operation. A cross-platform AD module using `ldap3` would enable real AD operations on non-Windows systems.

### No Database

System inventory and scheduled job results are stored in local JSON files (`reports/systems.json`, `reports/health_report_*.json`). This limits scalability, concurrency, and data integrity. No migration path to a proper database exists yet.

### Authentication Security

- Password comparison uses plaintext (`verify_password` warns to use bcrypt in production)
- Password hashing uses SHA-256 (`get_password_hash` warns it's insecure)
- Mock user database with hardcoded credentials in `src/api/middleware/auth.py`
- CORS allows all origins (`allow_origins=["*"]`)

### Connection Management

Each API request creates a new AD connection and disconnects in a `finally` block. There is no connection pooling, which adds latency and overhead under load.

### No Tests

The `tests/` directory is empty. No unit tests, integration tests, or test configuration exist.

---

## Future Integration Plans

### Short-Term

1. **ldap3-based AD client** — Implement a cross-platform AD connection class using `ldap3` as a fallback/alternative to `pyad`. This would enable real AD operations on Linux/macOS and could replace pyad as the primary client.

2. **Database migration** — Replace JSON file storage with SQLite (already listed as a dependency) or PostgreSQL for system inventory, job results, audit logs, and user sessions.

3. **Authentication hardening** — Replace plaintext/SHA-256 with bcrypt, move credentials to environment variables or a secrets manager, remove mock user database, restrict CORS origins.

4. **Test suite** — Add unit tests for all core modules (user management, group management, health checks, security audits, migration) and integration tests for the API endpoints.

5. **Connection pooling** — Implement a shared AD connection pool in the API layer to avoid creating a new connection per request.

### Medium-Term

6. **Azure AD sync productionization** — The `azure_ad.py` module is functional but needs error recovery, delta sync support, conflict resolution, and configurable sync schedules.

7. **Dashboard modernization** — Replace inline CSS templates with a frontend framework (React/Vue) and component library. Add real-time updates via WebSocket.

8. **Role-based access in dashboard** — Extend the existing API RBAC model to the web dashboard with proper session management and permission enforcement.

9. **Configuration externalization** — Move all settings from `config/settings.py` to environment variables with `.env` file support, validation, and secrets management (Vault integration).

10. **Containerization** — Add Dockerfile and docker-compose for the application, enabling consistent deployment across environments.

### Long-Term

11. **Homelab integration** — Integrate with the homelab infrastructure stack (Traefik reverse proxy, Vault for secrets, MinIO for report/artifact storage, PostgreSQL as the backend database, Prometheus metrics).

12. **Multi-domain support** — Support managing multiple AD forests/domains from a single AdminFlow instance with per-domain configuration.

13. **Audit trail** — Persistent audit logging for all AD operations with tamper-proof storage, searchable history, and compliance reporting.

14. **Plugin system** — Extensible plugin architecture for custom AD operations, third-party integrations, and custom reports.