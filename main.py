import json
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from database import init_db, get_db_connection
from schemas import LoginRequest, MessageRequest
from services import call_cpp_classifier, call_llama_model

app = FastAPI(title="TPU Virtual Support API MVP")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

init_db()

@app.post("/api/auth/login")
async def login(data: LoginRequest):
    conn = get_db_connection()
    user = conn.execute("SELECT * FROM users WHERE email = ?", (data.email,)).fetchone()
    conn.close()

    if not user:
        conn = get_db_connection()
        conn.execute("INSERT INTO users VALUES (?, 'user')", (data.email,))
        conn.commit()
        conn.close()
        role = "user"
    else:
        role = user["role"]

    return {
        "status": "success",
        "user": {
            "email": data.email,
            "role": role
        }
    }


@app.get("/api/admin/tickets")
async def get_tickets():
    conn = get_db_connection()
    tickets = conn.execute("SELECT * FROM tickets ORDER BY updated_at DESC").fetchall()
    conn.close()
    return [dict(ticket) for ticket in tickets]


@app.post("/api/chat/send")
async def send_message(data: MessageRequest):
    conn = get_db_connection()

    conn.execute("INSERT INTO messages (email, author, text) VALUES (?, 'user', ?)", (data.email, data.message))
    conn.commit()

    cpp_res = call_cpp_classifier(data.message)
    category = cpp_res["category"]

    if category != "unknown":
        kb_item = conn.execute("SELECT instruction FROM kb_articles WHERE category = ?", (category,)).fetchone()
        instruction = kb_item["instruction"] if kb_item else ""

        ticket = conn.execute("SELECT * FROM tickets WHERE email = ? AND category = ?",
                              (data.email, category)).fetchone()
        if not ticket:
            conn.execute("INSERT INTO tickets (email, category, status) VALUES (?, ?, 'Решено ботом')",
                         (data.email, category))
        else:
            conn.execute("UPDATE tickets SET status = 'Решено ботом', updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                         (ticket["id"],))
        conn.commit()

        system_prompt = f"Ты техподдержка ТПУ. Сформулируй вежливый ответ на основе контекста. КОНТЕКСТ: {instruction}"

    else:
        ticket = conn.execute("SELECT * FROM tickets WHERE email = ? AND status = 'Требуется уточнение'",
                              (data.email,)).fetchone()
        if not ticket:
            conn.execute("INSERT INTO tickets (email, category, status) VALUES (?, 'unknown', 'Требуется уточнение')",
                         (data.email,))
            conn.commit()

        system_prompt = "Ты техподдержка ТПУ. Пользователь дал мало информации. Задай вежливый уточняющий вопрос."

    bot_reply = call_llama_model(system_prompt, data.message)

    conn.execute("INSERT INTO messages (email, author, text) VALUES (?, 'bot', ?)", (data.email, bot_reply))
    conn.commit()
    conn.close()

    return {
        "author": "bot",
        "text": bot_reply,
        "detected_category": category
    }


@app.get("/api/chat/history")
async def get_chat_history(email: str):
    conn = get_db_connection()
    messages = conn.execute("SELECT author, text FROM messages WHERE email = ? ORDER BY timestamp ASC",
                            (email,)).fetchall()
    conn.close()
    return [dict(msg) for msg in messages]
