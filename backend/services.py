import json
import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

try:
    import tpu_classifier
    # На некоторых системах при отсутствии скомпилированного .pyd/.so файла
    # Python все равно молча создает пустой namespace-package с тем же именем
    # (если рядом лежит папка tpu_classifier без реального модуля). Поэтому
    # мало проверить, что import не упал — нужно убедиться, что в модуле
    # реально есть функция classify_request.
    CPP_MODULE_AVAILABLE = hasattr(tpu_classifier, "classify_request")
    if CPP_MODULE_AVAILABLE:
        print("[INFO] C++ classifier loaded successfully.")
    else:
        print("[WARNING] tpu_classifier найден, но не содержит classify_request "
              "(модуль не скомпилирован). Используется Python fallback.")
except ImportError as e:
    CPP_MODULE_AVAILABLE = False
    print(f"[WARNING] C++ module load failed: {e}")
    print("[WARNING] Using Python classifier fallback.")

import qwen_service


CATEGORY_ALIASES = {
    "корпоративная почта": "Корпоративная почта",
    "программное обеспечение": "ПО",
    "по": "ПО",
    "оборудование": "Оборудование",
    "wifi": "Wi-Fi",
    "wi-fi": "Wi-Fi",
    "vpn": "VPN",
    "доступы к аккаунту": "Доступы к аккаунту",
    "успеваемость и сессия": "Успеваемость и Сессия",
    "стипендии и выплаты": "Стипендии и Выплаты",
    "переводы и восстановление": "Переводы и Восстановление",
    "общежития": "Общежития",
    "время работы": "Время работы",
}


def normalize_category(category: str) -> str:
    value = (category or "unknown").strip()
    return CATEGORY_ALIASES.get(value.lower(), value)


def call_cpp_classifier(user_text: str) -> dict:
    if CPP_MODULE_AVAILABLE and hasattr(tpu_classifier, "classify_request"):
        try:
            result = json.loads(
                tpu_classifier.classify_request(
                    json.dumps({"message": user_text}, ensure_ascii=False)
                )
            )
            confidence = result.get("confidence", 0)
            if confidence > 1:
                confidence /= 100
            return {
                "category": normalize_category(result.get("category", "unknown")),
                "confidence": confidence,
            }
        except Exception as e:
            print(f"[C++ Runtime Error]: {e}")

    text = user_text.lower()
    rules = [
        (("wifi", "wi-fi", "вайфай", "вай фай", "интернет", "сеть"), "Wi-Fi", 0.96),
        (("vpn", "впн"), "VPN", 0.95),
        (("почт", "email", "e-mail", "mail"), "Корпоративная почта", 0.94),
        (("парол", "аккаунт", "учетн", "учётн", "логин", "войти"), "Доступы к аккаунту", 0.91),
        (("программ", "приложен", "установить", "установк", "ошибк\u0430 в программе"), "ПО", 0.90),
        (("ноутбук", "компьютер", "мыш", "клавиатур", "монитор", "оборудован"), "Оборудование", 0.90),
        (("оценк", "экзамен", "зачет", "зачёт", "сесс", "успеваем"), "Успеваемость и Сессия", 0.89),
        (("стипенд", "выплат", "денег"), "Стипендии и Выплаты", 0.89),
        (("перевод", "восстановлен", "восстановиться", "перевестись"), "Переводы и Восстановление", 0.88),
        (("общежит", "общаг", "комендант"), "Общежития", 0.90),
        (("время работ", "график", "когда работает"), "Время работы", 0.86),
    ]

    for keywords, category, confidence in rules:
        if any(word in text for word in keywords):
            return {"category": category, "confidence": confidence}

    return {"category": "unknown", "confidence": 0}


async def call_qwen(user_message: str, context: str | None = None) -> str:
    """
    Обращается к локальной модели Qwen2.5:7b (через Ollama, см. qwen_service.py).

    Используется ТОЛЬКО в тех ветках, где у C++ классификатора и векторного поиска
    нет готового ответа из базы знаний (см. main.py: сценарий "в ином случае").
    Если Ollama недоступна (не запущена локально), возвращается безопасный
    запасной ответ, чтобы демонстрация не падала без развернутой LLM.
    """
    try:
        answer = await qwen_service.generate_answer(user_message, context)
    except Exception as e:
        print(f"[Qwen exception]: {e}")
        answer = None

    if not answer or answer.startswith("Ошибка"):
        if context:
            return (
                "Я нашёл в базе знаний информацию, которая может относиться к вашему вопросу, "
                "но сейчас не могу связаться с локальной моделью Qwen, чтобы сформулировать ответ. "
                "Вот что удалось найти:\n\n"
                f"{context}\n\n"
                "Если это не помогло — нажмите «Нужен специалист»."
            )
        return (
            "Я получил ваше обращение, но пока не могу точно определить категорию проблемы "
            "(модель Qwen сейчас недоступна). Уточните, пожалуйста, с каким сервисом или "
            "оборудованием возникла проблема, либо нажмите «Нужен специалист»."
        )

    return answer
