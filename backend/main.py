import json
import os
import re

import chromadb
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from database import init_db, get_db_connection
from schemas import LoginRequest, MessageRequest, TicketCreateRequest, TicketReplyRequest
from services import call_cpp_classifier, call_qwen

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHROMA_PATH = os.path.join(PROJECT_DIR, "database", "chroma_db")

# ВАЖНО: имя коллекции должно совпадать с тем, что использовалось при наполнении
# базы (database/chroma_db). Раньше здесь стояло "university_knowledge" — такой
# коллекции не существовало, поэтому get_or_create_collection создавал новую,
# ПУСТУЮ коллекцию, и векторный поиск всегда возвращал 0 результатов.
CHROMA_COLLECTION_NAME = "tpu_kb"
# Порог "расстояния" (чем меньше — тем ближе смысл найденного документа к вопросу).
# Подобран эмпирически для дефолтной embedding-модели Chroma (all-MiniLM-L6-v2).
# При необходимости — откалибруйте под реальные запросы пользователей.
VECTOR_SEARCH_DISTANCE_THRESHOLD = 1.0

chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)
kb_collection = chroma_client.get_or_create_collection(name=CHROMA_COLLECTION_NAME)

app = FastAPI(title="TPU Virtual Support API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

init_db()


def save_message(conn, email, author, text):
    conn.execute(
        "INSERT INTO messages (email, author, text) VALUES (?, ?, ?)",
        (email, author, text),
    )


YES_PATTERN = re.compile(r"\b(да|ага|угу|верно|точно|именно|конечно)\b")
# "нет"/"неа" где угодно в сообщении, либо сообщение НАЧИНАЕТСЯ с отрицания "не"
# (например "не подключаюсь", "не могу"). Слово "не" в середине фразы не считаем
# отрицательным ответом, чтобы не путать с фразами вроде "да, но не сразу".
NO_PATTERN = re.compile(r"\b(нет|неа)\b|^не\b")


def detect_yes_no(text: str):
    """Простая эвристика да/нет для ответов на уточняющие вопросы категории."""
    t = text.lower().strip()
    has_yes = bool(YES_PATTERN.search(t))
    has_no = bool(NO_PATTERN.search(t))
    if has_yes and not has_no:
        return "yes"
    if has_no and not has_yes:
        return "no"
    return None


def build_kb_reply(category: str, kb_row) -> tuple[str, list]:
    """Формирует ответ и список шагов на основе конкретной статьи kb_articles."""
    try:
        steps = json.loads(kb_row["solution_steps"] or "[]")
    except (json.JSONDecodeError, TypeError):
        steps = []
    reply = (
        f"Спасибо за уточнение! Вот пошаговое решение для категории «{category}» "
        f"({kb_row['title']}) — выполните шаги ниже."
    )
    return reply, steps


@app.get("/")
async def root():
    return {"status": "ok", "message": "TPU Virtual Support API is running"}


@app.post("/api/auth/login")
async def login(data: LoginRequest):
    email = str(data.email).lower().strip()
    conn = get_db_connection()
    user = conn.execute("SELECT email, role FROM users WHERE email = ?", (email,)).fetchone()

    if user:
        role = user["role"]
    else:
        role = "admin" if email.startswith("admin@") else "user"
        conn.execute("INSERT INTO users (email, role) VALUES (?, ?)", (email, role))
        conn.commit()

    conn.close()
    return {"status": "success", "user": {"email": email, "role": role}}


@app.post("/api/chat/send")
async def send_message(data: MessageRequest):
    email = str(data.email).lower().strip()
    message = data.message.strip()

    if not message:
        raise HTTPException(status_code=400, detail="Сообщение не может быть пустым")

    conn = get_db_connection()
    normalized = message.lower().strip()

    # Кнопка «Решение помогло»
    if normalized == "решение помогло":
        conn.execute("DELETE FROM pending_clarifications WHERE email = ?", (email,))
        ticket = conn.execute(
            "SELECT * FROM tickets WHERE email = ? AND status != 'closed' ORDER BY id DESC LIMIT 1",
            (email,),
        ).fetchone()
        if ticket:
            conn.execute(
                "UPDATE tickets SET status = 'closed', updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (ticket["id"],),
            )
        save_message(conn, email, "user", message)
        reply = "Отлично! Рад, что решение помогло. Обращение закрыто. 😊"
        save_message(conn, email, "bot", reply)
        conn.commit()
        conn.close()
        return {
            "reply": reply,
            "category": ticket["category"] if ticket else None,
            "state": "finish",
            "options": None,
            "steps": None,
            "confidence": ticket["confidence"] if ticket else None,
        }

    # Кнопка «Нужен специалист».
    # Карточка обращения (тикет) в админ-панели создается ТОЛЬКО здесь — то есть
    # только тогда, когда пользователь сам попросил позвать специалиста. До этого
    # момента бот обрабатывает диалог самостоятельно, и в админ-панели ничего не
    # появляется.
    if normalized == "нужен специалист":
        conn.execute("DELETE FROM pending_clarifications WHERE email = ?", (email,))
        # Берем последнее реальное сообщение пользователя (не служебные кнопки),
        # чтобы у специалиста сразу был контекст проблемы, а не пустая карточка.
        prior_message_row = conn.execute(
            """
            SELECT text FROM messages
            WHERE email = ? AND author = 'user'
              AND LOWER(text) NOT IN ('нужен специалист', 'решение помогло')
            ORDER BY id DESC LIMIT 1
            """,
            (email,),
        ).fetchone()
        context_message = prior_message_row["text"] if prior_message_row else "Пользователь запросил специалиста без описания проблемы."

        classifier_result = call_cpp_classifier(context_message)
        category = classifier_result.get("category", "unknown")
        confidence = classifier_result.get("confidence", 0)

        ticket = conn.execute(
            "SELECT * FROM tickets WHERE email = ? AND status != 'closed' ORDER BY id DESC LIMIT 1",
            (email,),
        ).fetchone()

        if ticket:
            conn.execute(
                """
                UPDATE tickets
                SET status = 'open', category = ?, confidence = ?, message = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (category, confidence, context_message, ticket["id"]),
            )
        else:
            conn.execute(
                "INSERT INTO tickets (email, category, status, confidence, message) VALUES (?, ?, 'open', ?, ?)",
                (email, category, confidence, context_message),
            )

        save_message(conn, email, "user", message)
        reply = "Хорошо! Я передал ваше обращение специалисту технической поддержки. Ожидайте ответа."
        save_message(conn, email, "bot", reply)
        conn.commit()
        conn.close()
        return {
            "reply": reply,
            "category": category,
            "state": "specialist",
            "options": None,
            "steps": None,
            "confidence": confidence,
        }

    # Пользователь отвечает на ранее заданный уточняющий вопрос категории
    # (например бот спросил "Вы подключаетесь к беспроводной сети ТПУ?", а тут
    # приходит "Да"). Такое сообщение почти никогда не содержит ключевых слов
    # категории само по себе, поэтому классифицировать его заново с нуля нельзя —
    # нужно продолжить диалог с того места, где остановились.
    pending = conn.execute(
        "SELECT * FROM pending_clarifications WHERE email = ?", (email,)
    ).fetchone()

    if pending:
        save_message(conn, email, "user", message)
        category = pending["category"]
        question_index = pending["question_index"]

        category_row = conn.execute(
            "SELECT clarifying_questions FROM kb_categories WHERE category = ?",
            (category,),
        ).fetchone()
        try:
            clarifying_questions = json.loads(category_row["clarifying_questions"] or "[]") if category_row else []
        except (json.JSONDecodeError, TypeError):
            clarifying_questions = []

        # Порядок статей в kb_articles совпадает с порядком problems[] в bz.json,
        # который, в свою очередь, совпадает с порядком category_clarifying_questions —
        # поэтому i-й вопрос соответствует i-й статье базы знаний для этой категории.
        kb_rows = conn.execute(
            "SELECT id, title, solution_steps FROM kb_articles WHERE category = ? ORDER BY id ASC",
            (category,),
        ).fetchall()

        answer = detect_yes_no(message)
        bot_reply = None
        steps = None
        options = None
        confidence = None

        if answer == "yes" and question_index < len(kb_rows):
            # Ответ "да" на i-й уточняющий вопрос -> отдаем i-ю статью базы знаний.
            conn.execute("DELETE FROM pending_clarifications WHERE email = ?", (email,))
            bot_reply, steps = build_kb_reply(category, kb_rows[question_index])
            state = "finish"
            options = ["Решение помогло", "Нужен специалист"]

        elif answer == "no" and (question_index + 1) < len(clarifying_questions):
            # "Нет" -> переходим к следующему уточняющему вопросу той же категории.
            conn.execute(
                "UPDATE pending_clarifications SET question_index = ?, updated_at = CURRENT_TIMESTAMP WHERE email = ?",
                (question_index + 1, email),
            )
            bot_reply = clarifying_questions[question_index + 1]
            state = "clarification"
            options = ["Нужен специалист"]

        elif answer == "no":
            # Вопросы категории закончились, а точную проблему так и не определили —
            # отдаем первую статью категории как наиболее вероятный вариант.
            conn.execute("DELETE FROM pending_clarifications WHERE email = ?", (email,))
            if kb_rows:
                bot_reply, steps = build_kb_reply(category, kb_rows[0])
                state = "finish"
                options = ["Решение помогло", "Нужен специалист"]
            else:
                bot_reply = (
                    "Не удалось точно подобрать решение по вашим ответам. "
                    "Нажмите «Нужен специалист», чтобы обращение обработал оператор."
                )
                state = "clarification"
                options = ["Нужен специалист"]

        else:
            # Ответ не похож на явные "да"/"нет" — пользователь, вероятно, сразу
            # описал детали. Пробуем сопоставить по ключевым словам исходное
            # сообщение + этот ответ вместе, а не бросать контекст категории.
            conn.execute("DELETE FROM pending_clarifications WHERE email = ?", (email,))
            combined_text = f"{pending['original_message']} {message}".lower()

            kb_rows_kw = conn.execute(
                "SELECT title, keywords, solution_steps FROM kb_articles WHERE category = ?",
                (category,),
            ).fetchall()
            kb_item, best_score = None, 0
            for row in kb_rows_kw:
                try:
                    keywords = json.loads(row["keywords"] or "[]")
                except (json.JSONDecodeError, TypeError):
                    keywords = []
                score = sum(1 for keyword in keywords if str(keyword).lower() in combined_text)
                if score > best_score:
                    best_score = score
                    kb_item = row

            if kb_item is not None:
                bot_reply, steps = build_kb_reply(category, kb_item)
                state = "finish"
                options = ["Решение помогло", "Нужен специалист"]
            else:
                bot_reply = (
                    f"Пока не получается точно определить решение внутри категории «{category}» "
                    "по вашему описанию. Нажмите «Нужен специалист», и обращение передадут оператору."
                )
                state = "clarification"
                options = ["Нужен специалист"]

        save_message(conn, email, "bot", bot_reply)
        conn.commit()
        conn.close()
        return {
            "reply": bot_reply,
            "category": category,
            "state": state,
            "options": options,
            "steps": steps,
            "confidence": confidence,
        }

    # Обычное сообщение.
    #
    # Каскад обработки (именно в этом порядке, без создания тикетов на каждое
    # сообщение — карточка в админ-панели появляется только по кнопке
    # «Нужен специалист», см. обработчик выше):
    #   1. C++ классификатор пытается определить категорию.
    #   2. Если категория определена -> ответ строится из базы знаний (bz.json).
    #   3. Если категория НЕ определена -> подключается векторный поиск (ChromaDB).
    #   4. Если и векторный поиск ничего релевантного не нашел -> отвечает
    #      нейросеть Qwen (без готового контекста, вежливо уточняет детали).
    save_message(conn, email, "user", message)
    classifier_result = call_cpp_classifier(message)
    category = classifier_result.get("category", "unknown")
    confidence = classifier_result.get("confidence", 0)

    steps = None
    options = None

    # --- Шаг 2: категория определена -> ищем ответ строго в базе знаний ---
    if category != "unknown":
        kb_rows = conn.execute(
            "SELECT title, keywords, solution_steps FROM kb_articles WHERE category = ?",
            (category,),
        ).fetchall()

        message_lower = message.lower()
        kb_item = None
        best_score = 0

        for row in kb_rows:
            try:
                keywords = json.loads(row["keywords"] or "[]")
            except (json.JSONDecodeError, TypeError):
                keywords = []

            score = sum(1 for keyword in keywords if str(keyword).lower() in message_lower)
            if score > best_score:
                best_score = score
                kb_item = row

        if kb_item is not None:
            # Нашли конкретную статью базы знаний — отвечаем напрямую из нее,
            # без обращения к нейросети (быстрее и без риска "галлюцинаций").
            try:
                steps = json.loads(kb_item["solution_steps"] or "[]")
            except (json.JSONDecodeError, TypeError):
                steps = []

            bot_reply = (
                f"Я определил категорию обращения: «{category}» ({kb_item['title']}). "
                "Вот пошаговое решение из базы знаний ТПУ — выполните шаги ниже."
            )
            state = "finish"
            options = ["Решение помогло", "Нужен специалист"]

        else:
            # Категория ясна, но конкретную проблему внутри нее по ключевым словам
            # определить не удалось — задаем уточняющий вопрос из каталога услуг,
            # а не угадываем случайную инструкцию.
            category_row = conn.execute(
                "SELECT clarifying_questions FROM kb_categories WHERE category = ?",
                (category,),
            ).fetchone()
            try:
                clarifying_questions = json.loads(category_row["clarifying_questions"] or "[]") if category_row else []
            except (json.JSONDecodeError, TypeError):
                clarifying_questions = []

            if clarifying_questions:
                bot_reply = (
                    f"Я вижу, что ваш вопрос относится к категории «{category}», но мне нужно немного больше "
                    f"деталей, чтобы подобрать точное решение. {clarifying_questions[0]}"
                )
                # Запоминаем, что ждем ответ именно на 0-й вопрос этой категории —
                # иначе следующее сообщение ("Да"/"Нет") будет классифицировано
                # с нуля и потеряет весь контекст диалога.
                conn.execute(
                    """
                    INSERT INTO pending_clarifications (email, category, question_index, original_message, updated_at)
                    VALUES (?, ?, 0, ?, CURRENT_TIMESTAMP)
                    ON CONFLICT(email) DO UPDATE SET
                        category = excluded.category,
                        question_index = 0,
                        original_message = excluded.original_message,
                        updated_at = CURRENT_TIMESTAMP
                    """,
                    (email, category, message),
                )
            else:
                bot_reply = (
                    f"Я вижу, что ваш вопрос относится к категории «{category}», но мне нужно немного больше "
                    "деталей, чтобы подобрать точное решение. Опишите, пожалуйста, проблему подробнее."
                )
            state = "clarification"
            options = ["Нужен специалист"]

    # --- Шаг 3 и 4: категория не определена -> векторный поиск, иначе Qwen ---
    else:
        try:
            rag_results = kb_collection.query(
                query_texts=[message],
                n_results=1,
                include=["documents", "metadatas", "distances"],
            )
            retrieved_docs = rag_results.get("documents", [[]])[0]
            retrieved_meta = rag_results.get("metadatas", [[]])[0]
            retrieved_distances = rag_results.get("distances", [[]])[0]
        except Exception as e:
            print(f"[Chroma query error]: {e}")
            retrieved_docs, retrieved_meta, retrieved_distances = [], [], []

        found_via_vector_search = bool(
            retrieved_docs and retrieved_distances and retrieved_distances[0] <= VECTOR_SEARCH_DISTANCE_THRESHOLD
        )

        if found_via_vector_search:
            # Шаг 3: векторный поиск нашел релевантный прецедент в базе знаний.
            matched_category = retrieved_meta[0].get("category", category) if retrieved_meta else category
            matched_title = retrieved_meta[0].get("title") if retrieved_meta else None
            category = matched_category  # уточняем категорию, найденную семантическим поиском

            # У векторного поиска нет "confidence" в том же смысле, что у C++
            # классификатора — пересчитываем ее из distance (чем меньше distance,
            # тем ближе к 1.0), чтобы в UI отображалось осмысленное число, а не 0%.
            confidence = round(max(0.0, 1 - (retrieved_distances[0] / VECTOR_SEARCH_DISTANCE_THRESHOLD)) * 0.85 + 0.1, 2)

            # Пытаемся достать структурированные шаги для того же документа,
            # чтобы показать их пользователю списком (как и в шаге 2).
            if matched_title:
                kb_row = conn.execute(
                    "SELECT solution_steps FROM kb_articles WHERE category = ? AND title = ?",
                    (matched_category, matched_title),
                ).fetchone()
                if kb_row:
                    try:
                        steps = json.loads(kb_row["solution_steps"] or "[]")
                    except (json.JSONDecodeError, TypeError):
                        steps = []

            bot_reply = await call_qwen(message, context=retrieved_docs[0])
            state = "finish"
            options = ["Решение помогло", "Нужен специалист"]
        else:
            # Шаг 4: ни классификатор, ни векторный поиск не нашли готового ответа —
            # отвечает нейросеть Qwen без контекста из базы знаний. Системный промпт
            # Qwen (см. qwen_service.py) сам просит модель честно признать, что
            # готового ответа нет, и вежливо уточнить детали, а не выдумывать решение.
            bot_reply = await call_qwen(message, context=None)
            state = "clarification"
            options = ["Нужен специалист"]

    save_message(conn, email, "bot", bot_reply)
    conn.commit()
    conn.close()

    return {
        "reply": bot_reply,
        "category": category,
        "state": state,
        "options": options,
        "steps": steps,
        "confidence": confidence,
    }


@app.get("/api/chat/history")
async def get_chat_history(email: str):
    email = email.lower().strip()
    conn = get_db_connection()
    messages = conn.execute(
        "SELECT id, author, text, timestamp FROM messages WHERE email = ? ORDER BY timestamp ASC, id ASC",
        (email,),
    ).fetchall()
    conn.close()
    return [dict(message) for message in messages]


@app.get("/api/admin/tickets")
async def get_tickets():
    conn = get_db_connection()
    tickets = conn.execute(
        "SELECT id, email, category, status, confidence, message, admin_reply, created_at, updated_at FROM tickets ORDER BY updated_at DESC"
    ).fetchall()
    conn.close()
    return [dict(ticket) for ticket in tickets]


@app.post("/api/admin/tickets")
async def create_ticket(data: TicketCreateRequest):
    email = str(data.email).lower().strip()
    conn = get_db_connection()
    cursor = conn.execute(
        "INSERT INTO tickets (email, category, status, confidence, message) VALUES (?, ?, 'open', ?, ?)",
        (email, data.category, data.confidence, data.message),
    )
    conn.commit()
    ticket = conn.execute("SELECT * FROM tickets WHERE id = ?", (cursor.lastrowid,)).fetchone()
    conn.close()
    return dict(ticket)


@app.post("/api/admin/tickets/{ticket_id}/reply")
async def reply_to_ticket(ticket_id: int, data: TicketReplyRequest):
    reply = data.reply.strip()
    if not reply:
        raise HTTPException(status_code=400, detail="Ответ не может быть пустым")

    conn = get_db_connection()
    ticket = conn.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
    if not ticket:
        conn.close()
        raise HTTPException(status_code=404, detail="Обращение не найдено")

    conn.execute(
        "UPDATE tickets SET status = 'closed', admin_reply = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (reply, ticket_id),
    )
    save_message(conn, ticket["email"], "admin", reply)
    conn.commit()
    updated = conn.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
    conn.close()
    return {"status": "success", "ticket": dict(updated)}


@app.patch("/api/admin/tickets/{ticket_id}")
async def update_ticket(ticket_id: int, status: str):
    allowed = {"open", "in_progress", "closed", "Решено ботом", "Требуется уточнение"}
    if status not in allowed:
        raise HTTPException(status_code=400, detail="Недопустимый статус")

    conn = get_db_connection()
    cursor = conn.execute(
        "UPDATE tickets SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (status, ticket_id),
    )
    if cursor.rowcount == 0:
        conn.close()
        raise HTTPException(status_code=404, detail="Обращение не найдено")

    conn.commit()
    ticket = conn.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
    conn.close()
    return {"status": "success", "ticket": dict(ticket)}
