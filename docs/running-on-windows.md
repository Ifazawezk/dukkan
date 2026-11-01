# Running Dukkan on Windows

This guide uses PowerShell and needs no Make or other extra tools. You keep two terminals open: one for the API and one for the web app.

## What you need

- [Python 3.12](https://www.python.org/downloads/). During setup, tick "Add python.exe to PATH".
- [Node.js 22 or newer](https://nodejs.org/).
- [Git](https://git-scm.com/download/win).

Check them in a new PowerShell window:

```powershell
python --version
node --version
git --version
```

## First time setup

### 1. Get the code

```powershell
git clone https://github.com/Ifazawezk/dukkan.git
cd dukkan
```

### 2. Set up the API

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
copy .env.example .env
alembic upgrade head
```

`alembic upgrade head` creates the database. By default it is a single file, `backend\dukkan.db`.

### 3. Add the demo shop

```powershell
python -m app.cli seed
```

This creates Al Noor Mart, a mini market with two branches, 48 products and 45 days of trading. It takes about 10 to 20 seconds.

### 4. Start the API

```powershell
uvicorn app.main:app --reload
```

Leave this window open. The API docs are now at http://127.0.0.1:8000/docs.

### 5. Start the web app

Open a second PowerShell window in the `dukkan` folder:

```powershell
cd frontend
npm install
npm run dev
```

Leave this one open too, then go to **http://localhost:5173**.

### 6. Sign in

Use `owner`, `manager`, `rahul`, `maria` or `omar`. The password for all of them is `dukkan123`.

## Starting it again later

Terminal one:

```powershell
cd dukkan\backend
.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload
```

Terminal two:

```powershell
cd dukkan\frontend
npm run dev
```

## Useful commands

Run these from `backend` with the virtual environment active.

| Task | Command |
| --- | --- |
| Rebuild the demo shop, deleting all data | `python -m app.cli seed --reset` |
| Check stock against the ledger | `python -m app.cli verify-stock` |
| Create the first owner for a real shop | `python -m app.cli create-owner --username yourname` |
| Run the tests | `pytest` |
| Run the benchmark | `python scripts/bench_checkout.py` |

## Starting a real shop instead of the demo

Skip the seed step and create an owner:

```powershell
alembic upgrade head
python -m app.cli create-owner --username yourname
```

Start both servers and sign in. Then go to **Settings** to enter your shop name and add your first branch, and to **Products** to add what you sell. Set opening quantities from **Inventory** with **Adjust**.

Back up by copying `backend\dukkan.db` while the API is stopped.

## Using PostgreSQL

Create a database, then set the connection in `backend\.env`:

```
DUKKAN_DATABASE_URL=postgresql+psycopg://dukkan:yourpassword@localhost:5432/dukkan
```

Run `alembic upgrade head` again and restart the API.

## Common problems

**"running scripts is disabled on this system"** when activating the virtual environment. Allow scripts for the current window, then try again:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

**"npm" or "node" is not recognized.** Node.js is not on your PATH. Close and reopen PowerShell after installing it. If that does not help, add it for the current window:

```powershell
$env:PATH += ";C:\Program Files\nodejs"
```

**"uvicorn" or "alembic" is not recognized.** The virtual environment is not active. Run `.venv\Scripts\Activate.ps1` from the `backend` folder.

**Sign in fails, or the page shows errors.** The API is probably not running. Check that the first terminal is still open and that http://127.0.0.1:8000/api/health shows `"status":"ok"`.

**"no such table" in the API window.** The database has not been created. Run `alembic upgrade head`.

**"The database already has data"** when seeding. Use `python -m app.cli seed --reset`. This deletes everything in the database.

**Port 8000 is already in use.** Start the API on another port and point the web app at it:

```powershell
uvicorn app.main:app --reload --port 8001
```

```powershell
$env:DUKKAN_API_URL = "http://127.0.0.1:8001"
npm run dev
```

**Port 5173 is already in use.** Vite picks the next free port and prints it. Use the address it shows.
