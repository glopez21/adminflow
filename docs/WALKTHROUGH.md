# AdminFlow Walkthrough

End-to-end guide for running through the AdminFlow platform — from setup to
exploring every major feature.  No Active Directory environment is required; all
AD-dependent endpoints degrade gracefully with meaningful messages.

---

## 1. Prerequisites

- **Python** 3.10+
- **Docker** + **Docker Compose** (optional, for containerised runs)
- **uv** (recommended — install with `curl -LsSf https://astral.sh/uv/install.sh | sh`)

---

## 2. Setup

```bash
git clone <repo-url> adminflow
cd adminflow
uv sync
```

Verify the install:

```bash
uv run python --version               # 3.10+
uv run ruff check .                    # 0 errors
uv run mypy src/                       # 0 errors
uv run pytest tests/ -q               # 29 passed
```

---

## 3. Start the API Server

```bash
uv run python -m src.api.main
```

The server starts on **`http://localhost:8000`**.

Open the interactive API docs:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

---

## 4. Authenticate

AdminFlow supports two authentication methods:

### API Key (quick start)

All endpoints accept the header `X-API-Key: ad-admin-key-001` (defined in
`config/settings.py`).

```bash
curl -s -H "X-API-Key: ad-admin-key-001" http://localhost:8000/api/users | head -5
```

### JWT Token

```bash
# Obtain a token (form-data)
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/token \
  -d "username=admin" -d "password=admin123" | python -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# Use the token
curl -s -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/users | head -5
```

---

## 5. Explore Endpoints

Run the following in order to exercise every endpoint group.

### 5a. Users

```bash
BASE="http://localhost:8000/api"
AUTH="-H X-API-Key: ad-admin-key-001"

# List all users
curl -s $AUTH "$BASE/users"

# Create a user
curl -s -X POST $AUTH "$BASE/users" \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","email":"test@domain.com","first_name":"Test","last_name":"User"}'

# Get user details
curl -s $AUTH "$BASE/users/testuser"

# Find inactive users (90 days)
curl -s $AUTH "$BASE/users/inactive/90"
```

### 5b. Groups

```bash
# List all groups
curl -s $AUTH "$BASE/groups"

# Create a group
curl -s -X POST $AUTH "$BASE/groups" \
  -H "Content-Type: application/json" \
  -d '{"name":"TestGroup","scope":"Global","category":"Security"}'

# Get group members
curl -s $AUTH "$BASE/groups/TestGroup/members"

# Add member to group
curl -s -X POST $AUTH "$BASE/groups/add-member" \
  -H "Content-Type: application/json" \
  -d '{"group_name":"TestGroup","member_name":"testuser"}'

# Find empty groups
curl -s $AUTH "$BASE/groups/empty"
```

### 5c. Health Checks

```bash
# Run all checks
curl -s $AUTH "$BASE/health/"

# Replication status
curl -s $AUTH "$BASE/health/replication"

# Domain controllers
curl -s $AUTH "$BASE/health/domain-controllers"

# FSMO roles
curl -s $AUTH "$BASE/health/fsmo"

# DNS verification
curl -s $AUTH "$BASE/health/dns"
```

### 5d. Security Audits

```bash
# Run all audits
curl -s $AUTH "$BASE/security/"

# Privileged accounts
curl -s $AUTH "$BASE/security/privileged"

# Password policy
curl -s $AUTH "$BASE/security/password-policy"

# Inactive accounts
curl -s $AUTH "$BASE/security/inactive/90"

# Locked accounts
curl -s $AUTH "$BASE/security/locked"

# Network scan
curl -s -X POST $AUTH "$BASE/security/network-scan" \
  -H "Content-Type: application/json" \
  -d '{"network_range":"192.168.1.0/24","scan_types":["ping"]}'
```

### 5e. Systems (Inventory & Remote Connectivity)

```bash
# List all systems
curl -s $AUTH "$BASE/systems/"

# Add a system
curl -s -X POST $AUTH "$BASE/systems/" \
  -H "Content-Type: application/json" \
  -d '{"hostname":"srv-01","ip_address":"192.168.1.100","os":"Windows Server 2022"}'

# Get system details
curl -s $AUTH "$BASE/systems/1"

# Port scan
curl -s -X POST $AUTH "$BASE/systems/port-scan" \
  -H "Content-Type: application/json" \
  -d '{"host":"192.168.1.100","ports":[22,80,443,3389]}'

# Remote connection test
curl -s -X POST $AUTH "$BASE/systems/remote-connect" \
  -H "Content-Type: application/json" \
  -d '{"host":"192.168.1.100","connection_type":"ssh","port":22}'
```

### 5f. Migration

```bash
# Export user attributes
curl -s $AUTH "$BASE/migration/export/testuser"

# Batch move users
curl -s -X POST $AUTH "$BASE/migration/move" \
  -H "Content-Type: application/json" \
  -d '{"usernames":["testuser"],"target_ou":"ou=Archived,dc=domain,dc=com"}'

# Group mapping
curl -s -X POST $AUTH "$BASE/migration/group-mapping" \
  -H "Content-Type: application/json" \
  -d '{"source_group":"Domain Admins","target_group":"Backup Admins","mapping_type":"direct"}'
```

---

## 6. Interactive Demo

The project includes a scripted demo that starts the server, exercises every
endpoint, and prints formatted output:

```bash
uv run demo
```

Press **Ctrl+C** to stop.  See `src/demo.py` for the full script.

---

## 7. Docker

### API + Redis

```bash
docker compose up -d
curl -s http://localhost:8000/api/users -H "X-API-Key: ad-admin-key-001"
docker compose down
```

### Full Stack (with Celery Worker)

```bash
docker compose --profile full up -d
docker compose down
```

### Dev Mode (hot-reload + demo)

```bash
docker compose --profile dev up
```

### Production Build (multi-stage)

```bash
docker build -f Dockerfile.prod -t adminflow:latest .
docker run -d -p 8000:8000 adminflow:latest
```

---

## 8. Code Quality

```bash
# Lint
uv run ruff check .

# Type check
uv run mypy src/

# Tests
uv run pytest tests/ -v

# Tests with coverage
uv run pytest tests/ --cov=src --cov-report=term
```

---

## 9. Project Tour

```
src/
  api/main.py          # FastAPI app factory & router registration
  api/middleware/auth.py   # JWT + API key auth
  api/routes/          # users, groups, health, security, migration, systems, auth
  user_management/     # ad_user_manager, group_management
  health_checks/       # ad_health (replication, DCs, LDAP, FSMO, DNS)
  security/            # ad_security (privileged, password, inactive, locked)
  migration/           # ad_migration (CSV import, batch move, export)
  utils/               # ad_connection (+ pool), network, remote_connections,
                       # scheduler, cache, azure_ad, log_config
  tasks/               # celery.py (async task definitions)
  main.py              # CLI entry point
  demo.py              # Interactive demo script
tests/                 # 29 pytest tests (schemas, user manager)
config/settings.py     # pydantic-settings configuration
```

---

## 10. Expected Output (No AD Environment)

When run on a machine without Active Directory, all AD-dependent endpoints
return a structured response like:

```json
{
  "status": "unavailable",
  "message": "Active Directory connection not available (pyad requires Windows)",
  "results": []
}
```

The API still serves:
- System inventory CRUD
- Network scanning (ping, port scans)
- Remote connection tests (SSH, etc.)
- JWT authentication
- All non-AD endpoints

---

## 11. Troubleshooting

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| `ModuleNotFoundError: pyad` | Running on Linux | Expected — AD features gracefully degrade |
| Port 8000 in use | Another process | `lsof -i :8000` then `kill <pid>` |
| `uv` not found | Not installed | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| Docker build slow | No cache | Add `--cache-from type=gha` to build command |

---

## Appendix: Postman

Import `postman/AdminFlow.postman_collection.json` into Postman.  The collection
includes 30+ pre-configured requests in 8 folders with collection-level
`base_url` and `api_key` variables.
