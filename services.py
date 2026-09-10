import json
import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

try:
    # Импортируем под оригинальным именем, которое зашито внутри бинарника
    import tpu_classifier

    CPP_MODULE_AVAILABLE = True
except ImportError as e:
    print(f"[WARNING] C++ module load failed: {e}")
    print("Using Python Mock instead.")
    CPP_MODULE_AVAILABLE = False


def call_cpp_classifier(user_text: str) -> dict:
    if CPP_MODULE_AVAILABLE:
        try:
            input_data = {"message": user_text}
            json_input = json.dumps(input_data)

            # Вызываем функцию из модуля tpu_classifier
            json_output_str = tpu_classifier.classify_request(json_input)

            result = json.loads(json_output_str)
            return {
                "category": result.get("category", "unknown"),
                "confidence": result.get("confidence", 0)
            }
        except Exception as e:
            print(f"[C++ Runtime Error]: {e}")
            return {"category": "unknown", "confidence": 0}
    else:
        # Питоновская заглушка (оставляем без изменений)
        text_lower = user_text.lower()
        if "вайфай" in text_lower or "wifi" in text_lower or "интернет" in text_lower:
            return {"category": "Wi-Fi", "confidence": 98}
        elif "впн" in text_lower or "vpn" in text_lower:
            return {"category": "VPN", "confidence": 95}
        elif "почта" in text_lower or "mail" in text_lower:
            return {"category": "Корпоративная почта", "confidence": 92}
        return {"category": "unknown", "confidence": 0}


def call_llama_model(system_prompt: str, user_message: str) -> str:
    """
    Пока оставляем заглушку для Llama, её мы подключим на следующем шаге.
    """
    if "unknown" in system_prompt:
        return "Я получил ваше обращение, но мне не хватает конкретики. Уточните, пожалуйста, с каким именно сервисом ТПУ (Wi-Fi, VPN или почта) у вас возникла проблема?"

    # Имитируем красивый ответ на основе контекста
    return f"[Ответ Llama на основе ТПУ-Контекста]: Здравствуйте! Мы зафиксировали проблему. Согласно инструкциям университета: Для корректной работы сервиса, пожалуйста, используйте единый пароль от Личного Кабинета ТПУ."
