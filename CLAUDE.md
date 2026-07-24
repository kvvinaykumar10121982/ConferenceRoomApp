# Conference Room Booking System

## Project Overview

A small Flask + SQLAlchemy REST API for reserving shared conference rooms. It
manages three entities — **conference rooms**, **employees** (who organize
meetings), and **bookings** — and exposes JSON endpoints to browse rooms, view
a room's availability, list free time slots, and create / reschedule / cancel
bookings. Bookings are guarded against double-booking: any create or reschedule
that overlaps an existing scheduled booking in the same room is rejected with
HTTP 409. Intended audience is an internal office/workshop scenario (a front
desk or team calendar tool would call this API); it ships with a seed script
for sample data and is not hardened for production.

**Architecture:** an application factory (`create_app` in `app.py`) wires the
SQLite database, registers two resource blueprints (`routes/rooms.py`,
`routes/bookings.py`), and exposes `/health`. The shared SQLAlchemy instance
lives in `extensions.py`; models are in `models.py`; overlap-detection logic is
centralized in `utils/conflict.py`. The database file is `db/bookings.db`
(git-ignored) and is seeded by `db/seed_data.py`.

**Endpoints:**

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | Liveness check |
| GET | `/rooms` | List all rooms |
| GET | `/rooms/<id>` | Get one room |
| GET | `/rooms/<id>/availability` | List a room's **booked** slots (opt `?date=`) |
| GET | `/rooms/<id>/free-slots` | List a room's **free** 30-min slots for a day (opt `?date=`, default today) |
| GET | `/bookings` | List bookings (opt `?room_id=`, `?organizer_id=`) |
| GET | `/bookings/<id>` | Get one booking |
| POST | `/bookings` | Create a booking |
| PUT | `/bookings/<id>` | Reschedule a booking |
| DELETE | `/bookings/<id>` | Cancel a booking (soft delete) |

**Running it:**

```bash
# one-time: create the venv and install deps, then seed sample data
pip install -r requirements.txt
python db/seed_data.py          # wipes + seeds 5 rooms, 10 employees, 20 bookings
python app.py                   # dev server on http://localhost:5000
```

**Usage examples:**

```bash
# 1. List all rooms
curl http://localhost:5000/rooms

# 2. See when room 1 is free on a given day (30-min slots, 09:00-18:00)
curl "http://localhost:5000/rooms/1/free-slots?date=2025-07-01"

# 3. Create a booking (201 on success, 409 if the slot is taken)
curl -X POST http://localhost:5000/bookings \
  -H "Content-Type: application/json" \
  -d '{"room_id":1,"organizer_id":1,"start_time":"2025-07-10T14:00:00","end_time":"2025-07-10T15:00:00","meeting_title":"Design Review","attendees":6}'

# 4. Reschedule that booking (id 21) to a new window
curl -X PUT http://localhost:5000/bookings/21 \
  -H "Content-Type: application/json" \
  -d '{"start_time":"2025-07-10T16:00:00","end_time":"2025-07-10T17:00:00"}'

# 5. Cancel it (soft delete -> status becomes "cancelled")
curl -X DELETE http://localhost:5000/bookings/21
```

Every response uses the same envelope: `{"data": ..., "error": ..., "status": <code>}`.

## Tech Stack
- Language: Python 3.11
- Framework: Flask 3.0
- ORM: Flask-SQLAlchemy 3.1
- Database: SQLite (db/bookings.db)

## Coding Conventions

- **Uniform response envelope.** Every route returns
  `{'data': <payload-or-None>, 'error': <message-or-None>, 'status': <int>}`
  via `jsonify`, and the HTTP status code is set to match the `status` field
  (e.g. `return jsonify({...}), 404`). Keep new routes consistent with this.
- **Application-factory + shared extensions.** App construction lives in
  `create_app()`; the SQLAlchemy `db` instance lives in `extensions.py`. Models
  and routes import `from extensions import db` — **never** `from app import db`
  (see Do Not Touch).
- **One blueprint per resource, verb_noun handlers.** Routes are grouped into
  blueprints named `<resource>_bp` (`rooms_bp`, `bookings_bp`) in `routes/` and
  registered in `create_app`. Handler functions are named `verb_noun`
  (`get_rooms`, `create_booking`, `reschedule_booking`, `cancel_booking`).
- **Models serialize via `to_dict()`.** Never pass ORM objects to `jsonify`
  directly; each model exposes `to_dict()`, and datetimes are emitted as
  ISO-8601 strings with `.isoformat()`.
- **ISO-8601 in, validated.** Datetime and date inputs are parsed with
  `datetime.fromisoformat(...)`; invalid input returns HTTP 400 with a clear
  message rather than raising.
- **Soft delete, not hard delete.** Cancelling a booking sets
  `status='cancelled'` instead of removing the row; availability and conflict
  checks only consider `status='scheduled'` records.
- **Config as module-level constants.** Tunable values (e.g. `BUSINESS_START`,
  `BUSINESS_END`, `SLOT_MINUTES` in `routes/rooms.py`) are named constants at
  the top of the module, not magic numbers inline.
- **Google-style docstrings** on all methods and routes.

## Do Not Touch

- **The `from extensions import db` import boundary.** `models.py`, all
  `routes/*.py`, and `db/seed_data.py` import `db` from `extensions.py`, and
  only `app.py` / `seed_data.py` import `create_app` from `app`. Do **not**
  revert any of these to `from app import db` (or import route/model modules at
  the top of `app.py`). Doing so re-triggers `app = create_app()` mid-import
  and reintroduces the circular-import crash (`ImportError: cannot import name
  'bookings_bp'`) that makes `python app.py` fail to start.

## Useful Context

- **The seed data is all in the evening, which is why `free-slots` looks
  empty of bookings.** `db/seed_data.py` is destructive (`drop_all()` then
  `create_all()`) and inserts 20 bookings dated 2025-07-01 through 2025-07-05,
  every one in the 18:00–21:30 range. Since `free-slots` only covers the
  09:00–18:00 business day, seeded rooms show a full 18-slot free day. To see
  slots actually removed, create a daytime booking first. `db/bookings.db` is
  git-ignored, so a fresh clone has no data until `seed_data.py` is run.

- **Overlap logic is centralized and uses strict inequalities.**
  `utils/conflict.check_overlap(room_id, start, end, exclude_id=None)` is the
  single source of truth for "is this slot taken?" and is reused by
  `create_booking`, `reschedule_booking`, and `get_free_slots`. It compares
  with strict `<` / `>`, so **back-to-back bookings are allowed** (09:00–09:30
  then 09:30–10:00 do not conflict), and it ignores `cancelled` bookings.
  `exclude_id` lets a booking skip itself when rescheduling. Any new
  scheduling feature should call this rather than re-implementing overlap
  checks.
