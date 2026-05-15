# AdminFlow Known Issues & Conflicts

## Security Issues

### CRITICAL: Plaintext Password Storage
- **File**: `src/api/middleware/auth.py:68-79`
- **Description**: `USERS_DB` stores passwords in plaintext (`"admin123"`, `"service123"`, `"viewer123"`)
- **Impact**: Any attacker with file read access or DB access gains all credentials
- **Fix**: Replace `verify_password` with bcrypt, store hashed passwords, or remove hardcoded user DB entirely in favor of env vars / external auth
- **Status**: Open

### CRITICAL: Hardcoded Credentials
- **File**: `src/api/middleware/auth.py:49-53`
- **Description**: API keys are configured via env vars but fall back to hardcoded defaults (`ad-admin-key-001`, etc.)
- **Impact**: Easy to miss setting these in production, leaving default keys active
- **Fix**: Fail at startup if API keys are still defaults (compare against known default values)
- **Status**: Open

### HIGH: CORS Allows All Origins
- **File**: `src/api/main.py:147`
- **Description**: `allow_origins=["*"]` allows any website to make cross-origin requests
- **Impact**: CSRF-style attacks possible if any endpoint uses cookie/session auth
- **Fix**: Read from `settings.cors_allowed_origins` instead of hardcoded `["*"]`
- **Status**: Open

### MEDIUM: No Rate Limiting
- **Description**: No rate limiting on any API endpoint
- **Impact**: Brute force attacks against JWT auth endpoint are unthrottled
- **Fix**: Add rate limiting middleware or use a gateway (Traefik/NGINX)
- **Status**: Open

## Architecture Issues

### HIGH: Per-Request AD Connections
- **Files**: All route files in `src/api/routes/*.py`
- **Description**: Every API call creates a fresh `ADConnection` using `ADConnection(server, username, password, base_dn)` and disconnects immediately. `ADConnectionPool` exists (`src/utils/ad_connection.py:246`) but is never used by routes.
- **Impact**: Unnecessary latency on every request; no connection reuse under load
- **Fix**: Wire `ADConnectionPool.acquire()`/`release()` into all route handlers
- **Status**: Open

### HIGH: Dual Scheduler Conflict
- **Files**: `src/utils/scheduler.py` (APScheduler), `src/tasks/celery.py` (Celery)
- **Description**: Two separate scheduling systems with overlapping functionality. Both define similar jobs (health checks, security audits, inactive reports, config backups). APScheduler runs in-process, Celery runs distributed — but there's no clear boundary for which should handle what.
- **Impact**: Potential for double-execution. Maintenance burden. Unclear which system should be used for new scheduled tasks.
- **Fix**: Pick one. Celery for distributed/async (recommended), APScheduler for single-node simplicity (if Celery is overkill).
- **Status**: Open

### MEDIUM: JSON File vs SQLAlchemy Duality
- **Files**: `src/api/routes/systems.py`, `src/db/models.py`
- **Description**: SQLAlchemy models exist for `System`, `ScheduledJob`, `AuditLog` with a full Alembic migration, but the API routes for systems still read/write `reports/systems.json` directly. The DB session factory and CRUD service exist but are unused.
- **Impact**: Inconsistent data layer. JSON files don't support concurrent access, transactions, or queries.
- **Fix**: Migrate systems routes to use `src/db/crud.py` services. Alembic migration already exists.
- **Status**: Open

## Platform Issues

### HIGH: Windows-Only AD Operations
- **Files**: `src/user_management/ad_user_manager.py`, `src/user_management/group_management.py`, `src/health_checks/ad_health.py`, `src/security/ad_security.py`, `src/migration/ad_migration.py`
- **Description**: All AD operations use `pyad` which requires Windows + `pywin32`. On Linux, every method returns `{"status": "error", "message": "pyad not available"}`. The `ldap3` library is in dependencies but not integrated.
- **Impact**: The entire application is non-functional on Linux/macOS for real AD operations
- **Fix**: Implement `ldap3`-based backend as drop-in replacement for `pyad`
- **Fix Available**: `ldap3` is already in `uv.lock`
- **Status**: Open

### MEDIUM: Windows CLI Dependencies in Health Checks
- **File**: `src/health_checks/ad_health.py`
- **Description**: Several health checks rely on Windows-native CLI tools (`nltest`, `repadmin`, `netdom`) via subprocess
- **Impact**: These checks always fail on Linux
- **Fix**: Implement LDAP-based equivalents using `ldap3`
- **Status**: Open

### LOW: `mstsc` / `net view` in Remote Connections
- **File**: `src/utils/remote_connections.py`
- **Description**: RDP and SMB discovery use Windows-only commands
- **Impact**: Non-functional on Linux (graceful fallback exists)
- **Fix**: Replace with cross-platform equivalents (e.g., `python-rdp`, `smbprotocol`), or document as Windows-only features
- **Status**: Open

## Code Quality Issues

### MEDIUM: Dead Code — Legacy Logger
- **File**: `src/utils/logger.py`
- **Description**: The `ADLogger` class and `setup_logging` function coexist with `src/utils/log_config.py` which provides structlog-based configuration. The API's lifespan calls `setup_logging` from `logger.py`, not `log_config.py`.
- **Impact**: Two competing logging systems. structlog features (JSON output, context binding) are unused.
- **Fix**: Standardize on `log_config.py` (structlog), remove or deprecate `logger.py`
- **Status**: Open

### LOW: Inline CSS in Web Dashboard
- **File**: `web/app.py`, `web/templates/*.html`
- **Description**: All CSS is inline in Jinja2 templates (~200 lines duplicated across 12 templates)
- **Impact**: Maintenance burden. Difficult to theme or customize.
- **Fix**: Extract CSS to `web/static/style.css`, remove inline styles
- **Status**: Open

### LOW: No Test Coverage for Core Modules
- **Files**: All except `tests/test_schemas.py` and `tests/test_user_manager.py`
- **Description**: 11 of 13+ business modules have zero test coverage
- **Impact**: Refactoring risk. No regression protection.
- **Fix**: Add unit tests per Phase 2 of dev plan
- **Status**: Open

## Dependency Issues

### LOW: `pyad` Import Failure Pattern
- **Files**: `ad_connection.py:49-54`, `ad_user_manager.py:50-57`
- **Description**: `pyad` raises a generic `Exception` (not `ImportError`) when `pywin32` is missing. The current `try/except Exception` catches this correctly but the pattern differs between files (`ad_connection.py` uses a module-level try/except, `ad_user_manager.py` uses `os.name == "nt"` guard first).
- **Impact**: Inconsistent pattern makes maintenance harder
- **Fix**: Standardize on one pattern (module-level try/except Exception is simpler)
- **Status**: Open

## Tracking Legend

- **Status**: Open / In Progress / Fixed / Won't Fix
- **Priority**: CRITICAL / HIGH / MEDIUM / LOW
