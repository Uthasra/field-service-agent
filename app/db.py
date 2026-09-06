"""A tiny stand-in for the ERP tables an agent would really talk to.

SQLite keeps setup to zero. Swapping in Postgres later means changing
`connect()` and nothing else.
"""
import sqlite3
from datetime import datetime, timezone

from app.config import DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS assets (
    asset_id     TEXT PRIMARY KEY,
    name         TEXT NOT NULL,
    location     TEXT NOT NULL,
    manual_id    TEXT NOT NULL,
    installed_on TEXT NOT NULL,
    criticality  TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS parts (
    part_number TEXT PRIMARY KEY,
    description TEXT NOT NULL,
    on_hand     INTEGER NOT NULL,
    reorder_at  INTEGER NOT NULL,
    warehouse   TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS asset_parts (
    asset_id    TEXT NOT NULL,
    part_number TEXT NOT NULL,
    PRIMARY KEY (asset_id, part_number)
);
CREATE TABLE IF NOT EXISTS asset_history (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    asset_id  TEXT NOT NULL,
    event_on  TEXT NOT NULL,
    event     TEXT NOT NULL,
    technician TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS work_orders (
    wo_id       TEXT PRIMARY KEY,
    asset_id    TEXT NOT NULL,
    description TEXT NOT NULL,
    priority    TEXT NOT NULL,
    status      TEXT NOT NULL,
    created_at  TEXT NOT NULL
);
"""


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


SEED_ASSETS = [
    ("PMP-4412", "Feedwater Pump 4412", "Plant A / Boiler House", "centrifugal-pump",
     "2019-03-14", "high"),
    ("CHL-2201", "Chiller Unit 2201", "Plant A / Roof Deck", "hvac-chiller",
     "2021-07-02", "medium"),
    ("CNV-1180", "Packing Line Conveyor 1180", "Plant B / Line 3", "belt-conveyor",
     "2020-11-19", "high"),
]

SEED_PARTS = [
    ("SEAL-208", "Mechanical seal, 50 mm shaft", 4, 2, "WH-01"),
    ("BRG-6206", "Deep groove ball bearing 6206", 0, 3, "WH-01"),
    ("IMP-4412", "Impeller, 210 mm bronze", 1, 1, "WH-02"),
    ("FLT-C22", "Chiller air filter, 24x24", 12, 4, "WH-01"),
    ("BELT-1180", "Conveyor belt, 6 m PVC", 2, 1, "WH-02"),
    ("ROL-55", "Idler roller 55 mm", 18, 6, "WH-02"),
]

SEED_ASSET_PARTS = [
    ("PMP-4412", "SEAL-208"), ("PMP-4412", "BRG-6206"), ("PMP-4412", "IMP-4412"),
    ("CHL-2201", "FLT-C22"),
    ("CNV-1180", "BELT-1180"), ("CNV-1180", "ROL-55"),
]

SEED_HISTORY = [
    ("PMP-4412", "2026-02-11", "Seal replaced after gland leak", "T. Perera"),
    ("PMP-4412", "2026-05-30", "Vibration reading 6.1 mm/s, flagged for watch", "N. Silva"),
    ("PMP-4412", "2026-08-04", "Bearing grease topped up, no fault found", "T. Perera"),
    ("CHL-2201", "2026-06-21", "Filters changed, condenser coil cleaned", "R. Fonseka"),
    ("CNV-1180", "2026-07-15", "Belt tracking adjusted after edge wear", "M. Jayawardena"),
]


def init_db(reset: bool = False) -> None:
    if reset and DB_PATH.exists():
        DB_PATH.unlink()
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = connect()
    with conn:
        conn.executescript(SCHEMA)
        conn.executemany("INSERT OR REPLACE INTO assets VALUES (?,?,?,?,?,?)", SEED_ASSETS)
        conn.executemany("INSERT OR REPLACE INTO parts VALUES (?,?,?,?,?)", SEED_PARTS)
        conn.executemany("INSERT OR REPLACE INTO asset_parts VALUES (?,?)", SEED_ASSET_PARTS)
        if not conn.execute("SELECT 1 FROM asset_history LIMIT 1").fetchone():
            conn.executemany(
                "INSERT INTO asset_history (asset_id, event_on, event, technician)"
                " VALUES (?,?,?,?)", SEED_HISTORY)
    conn.close()


def next_wo_id(conn: sqlite3.Connection) -> str:
    n = conn.execute("SELECT COUNT(*) AS c FROM work_orders").fetchone()["c"]
    return f"WO-{10001 + n}"


if __name__ == "__main__":
    init_db(reset=True)
    print(f"seeded {DB_PATH}")
