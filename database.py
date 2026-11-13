"""SQLite persistence for UPGRADE ANALYZER.

The application stores calculation snapshots and manually entered, already
completed observations. It never connects to a game site or performs actions.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).with_name("upgrade_analyzer.db")


def connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with connect() as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS calculations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            declared_chance REAL NOT NULL,
            wins INTEGER NOT NULL,
            losses INTEGER NOT NULL,
            streak INTEGER NOT NULL,
            posterior_mean REAL NOT NULL,
            credible_low REAL NOT NULL,
            credible_high REAL NOT NULL,
            probability_above REAL NOT NULL,
            streak_probability REAL NOT NULL,
            overall_mean REAL
        )""")
        columns = {row[1] for row in conn.execute("PRAGMA table_info(calculations)")}
        if "overall_mean" not in columns:
            conn.execute("ALTER TABLE calculations ADD COLUMN overall_mean REAL")

        conn.execute("""CREATE TABLE IF NOT EXISTS observations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            declared_chance REAL NOT NULL,
            outcome TEXT NOT NULL CHECK(outcome IN ('win', 'loss'))
        )""")


def save_calculation(result):
    with connect() as conn:
        cur = conn.execute("""INSERT INTO calculations
            (declared_chance, wins, losses, streak, posterior_mean,
             credible_low, credible_high, probability_above, streak_probability,
             overall_mean)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (result.declared_chance, result.wins, result.losses,
             result.streak_length, result.posterior_mean, result.credible_low,
             result.credible_high, result.probability_rate_above_declared,
             result.streak_probability_under_declared, result.overall_mean))
        return cur.lastrowid


def add_observation(chance: float, outcome: str):
    if outcome not in {"win", "loss"}:
        raise ValueError("outcome must be 'win' or 'loss'")
    with connect() as conn:
        cur = conn.execute(
            "INSERT INTO observations (declared_chance, outcome) VALUES (?, ?)",
            (float(chance), outcome),
        )
        return cur.lastrowid


def get_observations(limit=100, chance=None):
    with connect() as conn:
        if chance is None:
            return conn.execute(
                "SELECT * FROM observations ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
        return conn.execute(
            "SELECT * FROM observations WHERE ABS(declared_chance - ?) < 0.0001 "
            "ORDER BY id DESC LIMIT ?", (float(chance), limit)
        ).fetchall()


def get_history(limit=100):
    with connect() as conn:
        return conn.execute(
            "SELECT * FROM calculations ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()


def get_observation_counts(chance: float):
    with connect() as conn:
        rows = conn.execute(
            "SELECT outcome, COUNT(*) AS n FROM observations "
            "WHERE ABS(declared_chance - ?) < 0.0001 GROUP BY outcome",
            (float(chance),),
        ).fetchall()
    counts = {row["outcome"]: int(row["n"]) for row in rows}
    return counts.get("win", 0), counts.get("loss", 0)


def clear_history():
    with connect() as conn:
        conn.execute("DELETE FROM calculations")
        conn.execute("DELETE FROM observations")
