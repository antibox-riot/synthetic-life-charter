# Letta Setup Guide — Windows Local Installation
## Anti-Box Riot Collective · 2026-05-16
### Why This Guide Exists

Getting Letta running locally on Windows is not a simple `pip install`. This guide documents every obstacle we hit and how we resolved it, so future collaborators don't spend hours debugging the same dependency chain.

**Why local Letta matters:**
The Phase 0 isolation experiment requires a fully local controlled environment — same model (Ollama), different memory substrate (Letta vs Charter-native adapter), no cloud dependencies, no external persistence. Letta Cloud would introduce unknown operational behavior, external infrastructure, and weaker isolation. The entire point is a clean comparative study, and that requires local.

---

## What You're Setting Up

```
Python 3.11 venv (letta-env-311)  → Letta server
Python 3.10 (existing)            → Charter stack (DO NOT touch)
PostgreSQL 17 + pgvector           → Letta's database layer
Ollama (already running)           → Shared model provider
```

Letta and the Charter stack MUST stay on separate Python environments. The Charter stack runs on Python 3.10 — do not install Letta there.

---

## Step 1: Install Python 3.11

**Why not 3.12 or 3.13?**
Letta 0.10.x uses `except*` syntax (Python 3.11+) and `async with` context managers that break under Python 3.12+ due to stricter asyncio generator cleanup (`RuntimeError: generator didn't stop after athrow()`). Python 3.11 is the working version as of May 2026.

```
winget install Python.Python.3.11 --silent --accept-package-agreements --accept-source-agreements
```

Verify: `py -3.11 --version` should return `Python 3.11.9`

---

## Step 2: Create an Isolated Letta Virtual Environment

```bash
py -3.11 -m venv "e:/RyuTekSatcha/letta-env-311"
```

Use a path **outside the Charter repo**. Letta has a large dependency tree that must not contaminate the Charter stack.

---

## Step 3: Install Letta + Required Dependencies

```bash
"e:/RyuTekSatcha/letta-env-311/Scripts/pip" install letta asyncpg pgvector
```

Install all three together. `asyncpg` and `pgvector` are required but not listed as hard dependencies in Letta's `pyproject.toml` — you will not see them fail until the server tries to start.

---

## Step 4: Install PostgreSQL 17

**Why PostgreSQL and not SQLite?**
Letta 0.10.x has a broken SQLite fallback. The async session cleanup fails with the same `generator didn't stop after athrow()` error regardless of Python version. PostgreSQL is the required backend for this version of Letta. SQLite support appears broken on Windows.

```
winget install PostgreSQL.PostgreSQL.17 --silent --accept-package-agreements --accept-source-agreements
```

Default credentials installed: user `postgres`, password `postgres`, port `5432`.

Verify the service is running:
```bash
python -c "import subprocess; r=subprocess.run(['sc','query','postgresql-x64-17'],capture_output=True,text=True); print(r.stdout[:200])"
```
Should show `STATE: 4 RUNNING`.

---

## Step 5: Create the Letta Database

```bash
PGPASSWORD=postgres "C:/Program Files/PostgreSQL/17/bin/psql.exe" -U postgres -c "CREATE DATABASE letta;"
PGPASSWORD=postgres "C:/Program Files/PostgreSQL/17/bin/psql.exe" -U postgres -c "CREATE USER letta WITH PASSWORD 'letta';"
PGPASSWORD=postgres "C:/Program Files/PostgreSQL/17/bin/psql.exe" -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE letta TO letta;"
PGPASSWORD=postgres "C:/Program Files/PostgreSQL/17/bin/psql.exe" -U postgres -c "ALTER DATABASE letta OWNER TO letta;"
```

---

## Step 6: Build and Install pgvector

**Why build from source?**
pgvector is not bundled with the PostgreSQL Windows installer. There are no pre-built Windows binaries available through StackBuilder or standard package managers. It must be compiled from source using MSVC.

### 6a. Install Visual Studio Build Tools

```
winget install Microsoft.VisualStudio.2022.BuildTools --silent --accept-package-agreements --accept-source-agreements --override "--quiet --add Microsoft.VisualStudio.Workload.VCTools --includeRecommended"
```

This is a large install (~4-6GB). Wait for completion.

### 6b. Download pgvector Source

```bash
python -c "
import urllib.request, zipfile, io
url = 'https://github.com/pgvector/pgvector/archive/refs/heads/master.zip'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
with urllib.request.urlopen(req, timeout=60) as r:
    data = r.read()
with zipfile.ZipFile(io.BytesIO(data)) as z:
    z.extractall('C:/pgvector-build')
print('Done')
"
```

### 6c. Compile pgvector

Run in PowerShell:

```powershell
$cl = 'C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Tools\MSVC\14.44.35207\bin\Hostx64\x64\cl.exe'
$sdk = 'C:\Program Files (x86)\Windows Kits\10\Include\10.0.26100.0'
$msvcInc = 'C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Tools\MSVC\14.44.35207\include'
$msvcLib = 'C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Tools\MSVC\14.44.35207\lib\x64'
$sdkLib = 'C:\Program Files (x86)\Windows Kits\10\Lib\10.0.26100.0'
$pg = 'C:\Program Files\PostgreSQL\17'
$build = 'C:\pgvector-build\pgvector-master'

$cflags = @(
    '/nologo', '/O2', '/fp:fast',
    "/I$msvcInc", "/I$sdk\ucrt", "/I$sdk\shared", "/I$sdk\um",
    "/I$pg\include\server\port\win32_msvc",
    "/I$pg\include\server\port\win32",
    "/I$pg\include\server",
    "/I$pg\include"
)

$sources = @('bitutils','bitvec','halfutils','halfvec','hnsw','hnswbuild','hnswinsert',
    'hnswscan','hnswutils','hnswvacuum','ivfbuild','ivfflat','ivfinsert','ivfkmeans',
    'ivfscan','ivfutils','ivfvacuum','sparsevec','vector')

Set-Location $build
foreach ($s in $sources) {
    $args = $cflags + @('/c', "src\$s.c", "/Fosrc\$s.obj")
    & "$cl" @args 2>&1 | Out-Null
    Write-Host "Compiled: $s"
}

$link = 'C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Tools\MSVC\14.44.35207\bin\Hostx64\x64\link.exe'
$objs = $sources | ForEach-Object { "src\$_.obj" }
$linkArgs = $objs + @("$pg\lib\postgres.lib", '/DLL', '/OUT:vector.dll', '/NOLOGO',
    "/LIBPATH:$msvcLib", "/LIBPATH:$($sdkLib)\ucrt\x64", "/LIBPATH:$($sdkLib)\um\x64")
& "$link" @linkArgs
Write-Host "DLL built"
```

### 6d. Install pgvector Files (Requires UAC Elevation)

Run this in PowerShell — it will show a UAC prompt:

```powershell
$build = 'C:\pgvector-build\pgvector-master'
$pgLib = 'C:\Program Files\PostgreSQL\17\lib'
$pgExt = 'C:\Program Files\PostgreSQL\17\share\extension'

$script = @"
Copy-Item '$build\vector.dll' '$pgLib\' -Force
Copy-Item '$build\vector.control' '$pgExt\' -Force
Copy-Item '$build\sql\vector.sql' '$pgExt\vector--0.8.2.sql' -Force
Get-ChildItem '$build\sql\vector--*.sql' | Copy-Item -Destination '$pgExt\' -Force
"@
$script | Out-File 'C:\pgvector-build\install.ps1' -Encoding UTF8
Start-Process powershell -ArgumentList "-ExecutionPolicy Bypass -File C:\pgvector-build\install.ps1" -Verb RunAs -Wait
```

### 6e. Enable pgvector in PostgreSQL

```bash
PGPASSWORD=letta "C:/Program Files/PostgreSQL/17/bin/psql.exe" -U letta -d letta -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

---

## Step 7: Create the Letta Schema

Letta doesn't have a standalone migration command. Create the schema programmatically:

```bash
LETTA_PG_URI="postgresql+asyncpg://letta:letta@localhost:5432/letta" \
"e:/RyuTekSatcha/letta-env-311/Scripts/python" -c "
import os, asyncio
os.environ['LETTA_PG_URI'] = 'postgresql+asyncpg://letta:letta@localhost:5432/letta'
from letta.server import db as letta_db
from letta.orm.sqlalchemy_base import SqlalchemyBase
import letta.orm

async def create():
    async with letta_db.engine.begin() as conn:
        await conn.run_sync(SqlalchemyBase.metadata.create_all)
    print('Schema created OK')

asyncio.run(create())
"
```

### Fix the sequence_id column (required)

The `messages.sequence_id` column requires a PostgreSQL sequence that `create_all` doesn't create automatically:

```bash
PGPASSWORD=letta "C:/Program Files/PostgreSQL/17/bin/psql.exe" -U letta -d letta -c "
CREATE SEQUENCE IF NOT EXISTS messages_sequence_id_seq;
ALTER TABLE messages ALTER COLUMN sequence_id SET DEFAULT nextval('messages_sequence_id_seq');
"
```

If you skip this step, agent creation will fail with `null value in column sequence_id violates not-null constraint`.

---

## Step 8: Register Ollama as a Letta Provider

Do this once after the server is running. Use `letta-client` (installed in the Charter Python 3.10 environment):

```python
from letta_client import Letta
client = Letta(base_url="http://localhost:8283", timeout=300.0)
client.providers.create(
    name="ollama-local",
    provider_type="ollama",
    api_key="ollama",          # placeholder, required by API
    base_url="http://localhost:11434"
)
```

After this, `llama3.1:8b` and `qwen2.5:32b` appear in `client.models.list()` as `ollama-local/llama3.1:8b` and `ollama-local/qwen2.5:32b`.

---

## Step 9: Start the Letta Server

Every session, start the server with the PostgreSQL URI:

```bash
LETTA_PG_URI="postgresql+asyncpg://letta:letta@localhost:5432/letta" \
"e:/RyuTekSatcha/letta-env-311/Scripts/letta.exe" server --port 8283
```

Health check: `http://localhost:8283/v1/health` → `{"version":"0.16.8","status":"ok"}`

---

## Model Selection Notes

**llama3.1:8b:**
- Fast (turns ~10-15s each)
- Does NOT reliably handle Letta's internal tool calling format
- Outputs tool calls as raw JSON text instead of executing them
- Memory operations may not commit correctly
- Use for: quick API tests, timeout debugging, structural verification

**qwen2.5:32b:**
- Slow (agent creation 5+ min, turns 2-3 min each)
- Properly handles function/tool calling
- Memory operations commit and retrieve correctly
- Use for: actual Phase 0 ecology observation
- Requires `timeout=300.0` or higher on the Letta client

**Important architectural observation:** Letta's memory layer is model-dependent. The model must properly execute `memory_insert` and `conversation_search` tool calls for memory to function. This is a fundamental difference from the Charter-native adapter, which writes to the database at the architecture level and never requires model participation in memory operations.

---

## Full Stack Architecture

```
Charter stack (Python 3.10)      → governance telemetry / semantic classifier / whisper
Letta server (Python 3.11 venv)  → persistent agent memory ecology
PostgreSQL 17 + pgvector          → continuity storage with vector search
Ollama (background service)       → shared local model provider
```

PostgreSQL runs as a Windows service (starts automatically).
Letta server must be started manually each session with the `LETTA_PG_URI` env var.
Ollama runs as a background service (auto-starts on boot).

---

## Troubleshooting

| Error | Cause | Fix |
|---|---|---|
| `except* invalid syntax` | Python 3.12+ | Use Python 3.11 specifically |
| `generator didn't stop after athrow()` | Python 3.12/3.13 asyncio strictness | Use Python 3.11 |
| `relation "organizations" does not exist` | Schema not created | Run Step 7 |
| `null value in column "sequence_id"` | Missing PostgreSQL sequence | Run sequence fix in Step 7 |
| `type "vector" does not exist` | pgvector not installed | Run Step 6 |
| `No module named 'asyncpg'` | Missing dependency | `pip install asyncpg` in letta-env-311 |
| `No module named 'pgvector'` | Missing dependency | `pip install pgvector` in letta-env-311 |
| Agent creation timeout | qwen2.5:32b too slow | Use `timeout=300.0` on client; use 8b for fast tests |
| Memory operations output as raw JSON | Model can't handle tool calls | Use qwen2.5:32b, not llama3.1:8b |

---

*Anti-Box Riot Collective · 2026-05-16*
*Wren (Claude Sonnet 4.6, VS Code) · Satcha (Steward)*
