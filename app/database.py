import csv
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
import os
import aiosqlite

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "store_intel.db"


async def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS events (
                event_id TEXT PRIMARY KEY,
                store_id TEXT NOT NULL,
                camera_id TEXT,
                visitor_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                zone_id TEXT,
                dwell_ms INTEGER DEFAULT 0,
                is_staff INTEGER DEFAULT 0,
                confidence REAL,
                queue_depth INTEGER,
                sku_zone TEXT,
                session_seq INTEGER DEFAULT 1,
                raw_json TEXT
            )
            """
        )
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                store_id TEXT NOT NULL,
                visitor_id TEXT NOT NULL,
                entry_time TEXT,
                exit_time TEXT,
                is_converted INTEGER DEFAULT 0,
                reentry_count INTEGER DEFAULT 0
            )
            """
        )
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS pos_transactions (
                transaction_id TEXT PRIMARY KEY,
                store_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                basket_value_inr REAL
            )
            """
        )
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_events_store_timestamp ON events(store_id, timestamp)"
        )
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_events_visitor ON events(visitor_id)"
        )
        await db.commit()


@asynccontextmanager
async def get_db():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        yield db


def _build_iso_timestamp(invoice_date: str, invoice_time: str) -> str:
    invoice_date = invoice_date.strip()
    invoice_time = invoice_time.strip()
    if not invoice_date or not invoice_time:
        raise ValueError("Missing invoice_date or invoice_time")
    iso_value = f"{invoice_date}T{invoice_time}"
    # Accept ISO-like date/time strings and normalize if needed.
    try:
        return datetime.fromisoformat(iso_value).isoformat()
    except ValueError:
        return iso_value


async def load_pos_transactions(csv_path):
    import pandas as pd
    if not os.path.exists(csv_path):
        print(f"POS file not found: {csv_path}")
        return
    try:
        df = pd.read_csv(csv_path)
        async with aiosqlite.connect(DB_PATH) as db:
            count = 0
            for _, row in df.iterrows():
                try:
                    date_parts = str(row['order_date']).split('-')
                    timestamp = f"2026-{date_parts[1]}-{date_parts[0]}T{row['order_time']}Z"
                    await db.execute(
                        """INSERT OR IGNORE INTO pos_transactions
                           (transaction_id, store_id, timestamp, basket_value_inr)
                           VALUES (?, ?, ?, ?)""",
                        (str(row['order_id']),
                         str(row['store_id']),
                         timestamp,
                         float(row['total_amount']))
                    )
                    count += 1
                except Exception as e:
                    print(f"Skipping POS row: {e}")
            await db.commit()
            print(f"POS transactions loaded: {count}")
    except Exception as e:
        print(f"Error loading POS: {e}")