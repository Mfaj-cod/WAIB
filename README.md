# WAIB — Flask + SQLite

Production-ready starter for WAIB with a real SQLite database using SQLAlchemy.

## Quickstart
1. (Optional) Create a virtualenv
2. `pip install -r requirements.txt`
3. Copy `.env.example` → `.env` and set a strong `SECRET_KEY` (and optionally `SQLITE_PATH`).
4. Run the app:
   ```bash
   flask --app app run --debug
   ```
5. Open http://127.0.0.1:5000

### Notes
- Database: SQLite (file path from `SQLITE_PATH` or default `waib.db`).
- Users: password hashing via Werkzeug.
- Contact messages stored in DB.
- Templates catalog stored in DB and auto-seeded on first run.
