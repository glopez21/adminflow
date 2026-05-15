# AdminFlow Development Notes

## Project Structure

```
adminflow/
├── src/                    # Main application package
│   ├── main.py             # CLI entry point (argparse)
│   ├── demo.py             # Interactive demo script
│   ├── api/                # FastAPI REST API
│   │   ├── main.py         # App factory, lifespan, CORS, routers
│   │   ├── middleware/auth.py  # JWT + API key + RBAC
│   │   ├── models/schemas.py   # Pydantic request/response models
│   │   └── routes/         # auth, users, groups, health, security, migration, systems
│   ├── db/                 # SQLAlchemy layer
│   │   ├── models.py       # System, ScheduledJob, AuditLog
│   │   ├── session.py      # Engine, session factory
│   │   └── crud.py         # SystemService, JobService, AuditService
│   ├── health_checks/ad_health.py
│   ├── migration/ad_migration.py
│   ├── security/ad_security.py
│   ├── tasks/celery.py     # Celery app + task definitions
│   ├── user_management/
│   │   ├── ad_user_manager.py
│   │   └── group_management.py
│   └── utils/
│       ├── ad_connection.py     # ADConnection + ADConnectionPool
│       ├── azure_ad.py          # AzureADManager + HybridADSync
│       ├── cache.py             # Redis CacheService
│       ├── log_config.py        # structlog config
│       ├── logger.py            # Legacy logging + ADLogger
│       ├── network.py           # Network scanning utilities
│       ├── remote_connections.py # SSH/RDP/VNC/WinRM/SMB handlers
│       └── scheduler.py         # APScheduler AutomationJob classes
├── tests/                  # Test suite
│   ├── test_schemas.py     # Pydantic schema tests
│   └── test_user_manager.py # ADUserManager mock tests
├── web/                    # Flask web dashboard
│   ├── app.py              # Flask app (475 lines, inline CSS)
│   └── templates/          # 12 Jinja2 templates
└── config/settings.py      # Pydantic-settings configuration
```

## Priority Roadmap

### Phase 1: Connection Pooling & Route Cleanup (Immediate)

| Task | Files | Effort | Impact |
|------|-------|--------|--------|
| Wire `ADConnectionPool` into all route files | `routes/users.py`, `groups.py`, `health.py`, `security.py`, `migration.py`, `systems.py` | Low | High — eliminates per-request connection overhead |
| Add pool lifecycle (init on startup, close on shutdown) | `api/main.py` lifespan | Low | High — ensures clean resource management |
| Standardize `get_*_manager()` pattern with pool | All route files | Low | High — consistent pattern across routes |

### Phase 2: Test Coverage (Short-term)

| Task | Files | Effort | Impact |
|------|-------|--------|--------|
| Unit tests for `ADGroupManager` | `group_management.py` | Medium | High — no existing group tests |
| Unit tests for `ADHealthChecker` | `ad_health.py` | Medium | High — no existing health tests |
| Unit tests for `ADSecurityAuditor` | `ad_security.py` | Medium | High — no existing security tests |
| Unit tests for `ADMigrationManager` | `ad_migration.py` | Medium | Medium |
| Unit tests for network utils | `network.py` | Medium | Medium |
| Unit tests for remote connections | `remote_connections.py` | Medium | Medium |
| Unit tests for scheduler | `scheduler.py` | Medium | Medium |
| Unit tests for Azure AD | `azure_ad.py` | Medium | Low (no Azure in CI) |
| API route integration tests | FastAPI TestClient | High | High — exercises full request/response cycle |

### Phase 3: Authentication Hardening (Short-term)

| Task | Files | Effort | Impact |
|------|-------|--------|--------|
| Replace plaintext password check with bcrypt | `auth.py` middleware | Low | Critical — security |
| Remove hardcoded `USERS_DB` with env vars or DB | `auth.py` middleware, `settings.py` | Low | Critical — security |
| Restrict CORS origins from settings | `api/main.py` | Low | High — security |
| Add rate limiting middleware | New file or config | Medium | Medium |

### Phase 4: JSON → SQLite Migration (Medium-term)

| Task | Files | Effort | Impact |
|------|-------|--------|--------|
| Route system CRUD through SQLAlchemy models | `routes/systems.py`, `db/crud.py` | Medium | High — consistency |
| Replace `reports/systems.json` with DB queries | `routes/systems.py` | Medium | High |
| Store job results in DB instead of JSON files | `tasks/celery.py`, `scheduler.py` | Medium | Medium |
| Add Alembic migration for audit_logs usage | `alembic/` | Low | Medium |

### Phase 5: ldap3 Cross-Platform Backend (Medium-term)

| Task | Files | Effort | Impact |
|------|-------|--------|--------|
| Implement `LDAP3Connection` class | New file or `ad_connection.py` | Medium | High — enables Linux AD ops |
| Add connection factory to select backend | `ad_connection.py` | Low | High |
| Update `ADUserManager` to use abstract backend | `ad_user_manager.py` | Medium | High |
| Update all business modules | 6+ files | High | High |

### Phase 6: Infrastructure & Polish (Long-term)

| Task | Effort | Impact |
|------|--------|--------|
| Consolidate APScheduler vs Celery (pick one) | Medium | Low (works now) |
| Web dashboard CSS → static files | Low | Medium |
| API client SDK from OpenAPI schema | Medium | Medium |
| WebSocket event stream for real-time alerts | Medium | Medium |
| Multi-domain/forest support | High | Medium |
| Plugin system for custom AD ops | High | Low |

## Testing Strategy

### Current State
- 29 tests across 2 files (schemas + user manager)
- All use mocking — no real AD dependency
- Good pattern: mock ADConnection, test return types and dict structures

### Patterns to Follow
```python
# Mock-based unit test pattern
from unittest.mock import Mock, patch

def test_some_method():
    mock_conn = Mock()
    mock_conn.server = "dc01.domain.com"
    manager = SomeManager(mock_conn)
    result = manager.some_method()
    assert isinstance(result, dict)
    assert "status" in result
```

### Coverage Targets
- **Critical** (must have): `ADGroupManager`, `ADHealthChecker`, `ADSecurityAuditor`
- **High** (should have): `ADMigrationManager`, `network.py`, `remote_connections.py`
- **Medium** (nice to have): `scheduler.py`, `azure_ad.py`, `cache.py`

## Connection Pool Pattern

All API routes currently follow this pattern:
```python
conn = ADConnection(server, username, password, base_dn)
conn.connect()
manager = SomeManager(conn)
try:
    result = manager.some_method()
    return result
finally:
    conn.disconnect()
```

Target pattern using pool:
```python
pool = get_ad_pool()  # global singleton, initialized at app startup
conn = pool.acquire(server, username, password, base_dn)
manager = SomeManager(conn)
try:
    result = manager.some_method()
    return result
finally:
    pool.release(conn)
```

## Environment Configuration

Key settings (via `.env` file):
- `AD_SERVER`, `AD_USER`, `AD_PASSWORD`, `AD_BASE_DN`
- `JWT_SECRET_KEY`, `JWT_ALGORITHM`
- `CORS_ALLOWED_ORIGINS`
- `DATABASE_URL` (default: `sqlite:///adminflow.db`)
- `LOG_LEVEL`, `LOG_FILE`

## CLI Commands

```bash
# Run API server
uvicorn src.api.main:app --host 0.0.0.0 --port 8000

# Run tests
uv run pytest tests/ -v

# Lint
uv run ruff check src/

# Type check
uv run mypy src/

# Run demo
uv run python -m src.demo
```
