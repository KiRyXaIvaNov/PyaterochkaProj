import json
import os
import sqlite3

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(BASE_DIR)
DB_NAME = os.path.join(PROJECT_DIR, "database", "database.db")
BZ_NAME = os.path.join(PROJECT_DIR, "database", "bz.json")


def get_db_connection():
    conn = sqlite3.connect(DB_NAME, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout = 30000")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def init_db():
    os.makedirs(os.path.dirname(DB_NAME), exist_ok=True)
    conn = get_db_connection()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            email TEXT PRIMARY KEY,
            role TEXT NOT NULL DEFAULT 'user'
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL,
            author TEXT NOT NULL,
            text TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL,
            category TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'open',
            confidence REAL,
            message TEXT,
            admin_reply TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS kb_articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT NOT NULL,
            title TEXT NOT NULL,
            keywords TEXT,
            solution_steps TEXT NOT NULL
        )
    """)

    # Уточняющие вопросы уровня категории (используются, когда C++ классификатор
    # определил категорию, но внутри нее не удалось понять конкретную проблему).
    conn.execute("""
        CREATE TABLE IF NOT EXISTS kb_categories (
            category TEXT PRIMARY KEY,
            clarifying_questions TEXT
        )
    """)

    # Состояние "бот ждет ответ на уточняющий вопрос" для конкретного пользователя.
    # Без этой таблицы бот на каждое новое сообщение заново гонял его через
    # C++ классификатор с нуля и "забывал", что секунду назад уже спросил
    # "Вы подключаетесь к беспроводной сети ТПУ?" — короткий ответ вроде "Да"
    # не содержит ключевых слов категории и улетал в Qwen как случайный вопрос.
    conn.execute("""
        CREATE TABLE IF NOT EXISTS pending_clarifications (
            email TEXT PRIMARY KEY,
            category TEXT NOT NULL,
            question_index INTEGER NOT NULL DEFAULT 0,
            original_message TEXT,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    count = conn.execute("SELECT COUNT(*) AS count FROM kb_articles").fetchone()["count"]
    if count == 0 and os.path.exists(BZ_NAME):
        with open(BZ_NAME, "r", encoding="utf-8") as f:
            data = json.load(f)

        for item in data:
            category = str(item.get("category", "")).strip()
            if not category:
                continue

            clarifying_questions = item.get("category_clarifying_questions", [])
            conn.execute(
                "INSERT OR REPLACE INTO kb_categories (category, clarifying_questions) VALUES (?, ?)",
                (category, json.dumps(clarifying_questions, ensure_ascii=False)),
            )

            for problem in item.get("problems", []):
                title = str(problem.get("title", "")).strip()
                if not title:
                    continue
                keywords = problem.get("keywords", [])
                steps = problem.get("solution_steps", [])
                conn.execute(
                    "INSERT INTO kb_articles (category, title, keywords, solution_steps) VALUES (?, ?, ?, ?)",
                    (
                        category,
                        title,
                        json.dumps(keywords, ensure_ascii=False),
                        json.dumps(steps, ensure_ascii=False),
                    ),
                )

    conn.commit()
    conn.close()
