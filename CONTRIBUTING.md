# Contributing to Dukkan

Thanks for helping. Bug reports, translation fixes and pull requests are all welcome. For a large change, please open an issue first so we can agree on the approach before you spend time on it.

## Development setup

You need Python 3.12, Node.js 22 or newer, and Git.

Backend:

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
copy .env.example .env
alembic upgrade head
python -m app.cli seed
uvicorn app.main:app --reload
```

Frontend, in a second terminal:

```powershell
cd frontend
npm install
npm run dev
```

The app is at http://localhost:5173 and the API docs are at http://127.0.0.1:8000/docs. The [Windows run guide](docs/running-on-windows.md) covers common problems. On macOS or Linux, activate the virtual environment with `source .venv/bin/activate` and use `cp` instead of `copy`.

## Running the checks

Run these before you open a pull request. They are the same checks every commit in this project was held to.

Backend, from `backend/`:

```powershell
pytest                 # the whole suite, warnings count as failures
pytest --cov           # with a coverage report
ruff check .           # lint
ruff format --check .  # formatting
```

Frontend, from `frontend/`:

```powershell
npm run build          # type check and production build
npm run format:check   # formatting
```

The frontend has no automated tests yet, so try your change in the browser, in both English and Arabic.

## Code style

**Python.** Ruff handles lint and formatting, with a line length of 100. Keep routers thin: parse the request, call a service, return the result. Business rules live in `app/services`. Services do not commit; the router commits once the whole operation has succeeded, so a failure anywhere rolls everything back.

**TypeScript.** Strict mode and Prettier, with a line length of 100. Use logical Tailwind classes such as `ms-2` and `text-start` rather than `ml-2` and `text-left`, so the layout mirrors correctly in Arabic.

**Comments.** Explain why, not what. Plain language, please.

## Rules that keep the data honest

- **Never change stock directly.** All stock changes go through `record_movement` in `app/services/inventory.py`. Do not write to `stock_levels` anywhere else.
- **Never use floats for money.** Use `Decimal` and the `Money()` column type, and round with `q()` from `app/money.py`.
- **Keep the two pricing files in step.** If you change the rules in `app/services/pricing.py`, make the same change in `frontend/src/lib/pricing.ts`.
- **Use UTC timestamps and business dates.** Store aware UTC datetimes, and use a sale's `business_date` for anything grouped by day.

## Database changes

After changing a model, create a migration from `backend/`:

```powershell
alembic revision --autogenerate -m "describe the change"
```

Read the generated file before committing it. Autogenerate does not notice a new check constraint on an existing table, so add those by hand in both `upgrade` and `downgrade`. `tests/test_migrations.py` fails if the migrations and models disagree.

## Translations

Every piece of interface text lives in `frontend/src/i18n/en.ts` and `ar.ts`. Add new keys to both files. The build fails if a key is missing from Arabic, which is deliberate. Arabic improvements from native speakers are especially welcome.

## Commits

Write short, imperative messages such as `Add stock transfers between branches`. Keep each commit working on its own, with tests and the build passing.

## Pull request checklist

- [ ] `pytest` passes, and new behaviour has tests
- [ ] `ruff check .` and `ruff format --check .` are clean
- [ ] `npm run build` and `npm run format:check` pass
- [ ] Stock changes go through `record_movement`
- [ ] A migration is included if a model changed, and you have read it
- [ ] New text exists in both English and Arabic
- [ ] Screens you touched were checked in both languages
- [ ] The README is updated if behaviour or commands changed
