from __future__ import annotations

from flask import Flask, jsonify, render_template, request
from analysis_engine import analyze
import database

app = Flask(__name__)
app.config["JSON_SORT_KEYS"] = False
database.init_db()


def error(message: str, status: int = 400):
    return jsonify({"error": message}), status


def parse_chance(value):
    try:
        chance = float(value)
    except (TypeError, ValueError):
        raise ValueError("Введите шанс числом.")
    if not 0 < chance < 100:
        raise ValueError("Шанс должен быть больше 0 и меньше 100.")
    return chance


def parse_count(value, label):
    try:
        number = int(value)
    except (TypeError, ValueError):
        raise ValueError(f"Поле «{label}» должно быть целым числом.")
    if number < 0:
        raise ValueError(f"Поле «{label}» не может быть отрицательным.")
    return number


def serialize_analysis(result):
    return {
        "chance": result.declared_chance,
        "wins": result.wins,
        "losses": result.losses,
        "attempts": result.attempts,
        "empirical": result.empirical_rate,
        "posterior": result.posterior_mean,
        "low": result.credible_low,
        "high": result.credible_high,
        "above": result.probability_rate_above_declared,
        "streak": result.streak_length,
        "streak_probability": result.streak_probability_under_declared,
        "overall": result.overall_mean,
    }


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/health")
def health():
    return jsonify({"status": "ok"})


@app.get("/api/summary")
def summary():
    try:
        chance = parse_chance(request.args.get("chance", "30"))
        wins, losses = database.get_observation_counts(chance)
        result = analyze(chance, wins, losses, min(losses, 0))
        return jsonify(serialize_analysis(result))
    except ValueError as exc:
        return error(str(exc))


@app.post("/api/observations")
def add_observation():
    data = request.get_json(silent=True) or {}
    try:
        chance = parse_chance(data.get("chance"))
        outcome = data.get("outcome")
        if outcome not in ("win", "loss"):
            return error("Выберите завершённый результат: победа или поражение.")
        database.add_observation(chance, outcome)
        wins, losses = database.get_observation_counts(chance)
        result = analyze(chance, wins, losses)
        return jsonify({"saved": True, "analysis": serialize_analysis(result)}), 201
    except ValueError as exc:
        return error(str(exc))


@app.post("/api/calculate")
def calculate():
    data = request.get_json(silent=True) or {}
    try:
        chance = parse_chance(data.get("chance"))
        wins = parse_count(data.get("wins", 0), "Победы")
        losses = parse_count(data.get("losses", 0), "Поражения")
        streak = parse_count(data.get("streak", 0), "Серия поражений")
        if streak > losses:
            return error("Текущая серия не может быть больше общего числа поражений.")
        result = analyze(chance, wins, losses, streak)
        database.save_calculation(result)
        return jsonify(serialize_analysis(result))
    except ValueError as exc:
        return error(str(exc))


@app.get("/api/history")
def history():
    obs = database.get_observations(limit=200)
    calcs = database.get_history(limit=100)
    items = []
    for row in obs:
        items.append({
            "id": row["id"], "type": "result", "date": row["created_at"],
            "chance": row["declared_chance"], "outcome": row["outcome"]
        })
    for row in calcs:
        items.append({
            "id": row["id"], "type": "calculation", "date": row["created_at"],
            "chance": row["declared_chance"], "wins": row["wins"],
            "losses": row["losses"], "overall": row["overall_mean"]
        })
    items.sort(key=lambda item: item["date"], reverse=True)
    return jsonify(items[:250])


@app.get("/api/stats")
def stats():
    items = database.get_observations(limit=1000)
    wins = sum(1 for row in items if row["outcome"] == "win")
    losses = sum(1 for row in items if row["outcome"] == "loss")
    total = wins + losses
    return jsonify({
        "total": total, "wins": wins, "losses": losses,
        "rate": (wins / total * 100) if total else None,
        "recent": [
            {"date": row["created_at"], "chance": row["declared_chance"],
             "outcome": row["outcome"]}
            for row in reversed(items[:30])
        ]
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
