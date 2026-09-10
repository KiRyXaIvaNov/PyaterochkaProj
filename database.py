import sqlite3

DB_NAME = "tpu_support.db"


def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # 1. Таблица пользователей
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        email TEXT PRIMARY KEY,
        role TEXT NOT NULL
    )""")

    # 2. Таблица истории сообщений
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT,
        author TEXT,
        text TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )""")

    # 3. Таблица карточек обращений (тикетов) для админа
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS tickets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT,
        category TEXT,
        status TEXT,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )""")

    # 4. База знаний (kb_articles) с инструкциями ТПУ
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS kb_articles (
        category TEXT PRIMARY KEY,
        instruction TEXT
    )""")

    # Забиваем тестовые данные (заглушки для демонстрации)
    cursor.executemany("INSERT OR IGNORE INTO users VALUES (?, ?)", [
        ("admin@tpu.ru", "admin"),
        ("student@tpu.ru", "user")
    ])

    cursor.executemany("INSERT OR IGNORE INTO kb_articles VALUES (?, ?)", [
        ("Wi-Fi",
         "Для подключения к сети TPU-Student используйте ваш логин и пароль от Личного Кабинета ТПУ (Данилы). Сеть доступна во всех учебных корпусах."),
        ("VPN",
         "Инструкция для VPN: Скачайте Cisco AnyConnect с сайта it.tpu.ru. Введите адрес шлюза vpn.tpu.ru и авторизуйтесь по единой учетной записи."),
        ("Корпоративная почта",
         "Корпоративная почта ТПУ доступна по адресу mail.tpu.ru. Вход осуществляется строго под вашей доменной учетной записью.")
    ])

    conn.commit()
    conn.close()


# Функции-помощники для работы с БД
def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row  # Чтобы возвращать данные в виде словарей
    return conn
