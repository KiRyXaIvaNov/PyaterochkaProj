#include <iostream>
#include <string>
#include <vector>
#include <unordered_map>
#include <algorithm>
#include <sstream>
#include "json.hpp" // nlohmann/json
#include <pybind11/pybind11.h>

using json = nlohmann::json;

// 1. АЛГОРИТМ ЛЕВЕНШТЕЙНА (расчет расстояния между словами для отлова опечаток)
int get_levenshtein_distance(const std::string& s1, const std::string& s2) {
    int m = s1.size();
    int n = s2.size();
    std::vector<std::vector<int>> dp(m + 1, std::vector<int>(n + 1));

    for (int i = 0; i <= m; i++) dp[i][0] = i;
    for (int j = 0; j <= n; j++) dp[0][j] = j;

    for (int i = 1; i <= m; i++) {
        for (int j = 1; j <= n; j++) {
            if (s1[i - 1] == s2[j - 1]) {
                dp[i][j] = dp[i - 1][j - 1];
            }
            else {
                dp[i][j] = 1 + std::min({
                    dp[i - 1][j],     // Удаление
                    dp[i][j - 1],     // Вставка
                    dp[i - 1][j - 1]  // Замена
                    });
            }
        }
    }
    return dp[m][n];
}

// 2. ФУНКЦИЯ ПРЕДОБРАБОТКИ И ТОКЕНИЗАЦИИ ТЕКСТА
std::vector<std::string> preprocess_and_tokenize(std::string text) {
    for (char& c : text) {
        // Проверяем знаки препинания только для стандартных ASCII символов, чтобы не сломать UTF-8
        if (c > 0 && std::ispunct(static_cast<unsigned char>(c))) {
            c = ' ';
        }
    }

    // Разбиваем строку на токены (слова)
    std::vector<std::string> tokens;
    std::stringstream ss(text);
    std::string token;

    // Список базовых стоп-слов
    const std::unordered_map<std::string, bool> stop_words = {
        {"у", true}, {"меня", true}, {"не", true}, {"и", true}, {"в", true},
        {"na", true}, {"что", true}, {"как", true}
    };

    while (ss >> token) {
        if (stop_words.find(token) == stop_words.end()) {
            tokens.push_back(token);
        }
    }
    return tokens;
}

// 3. ГЛАВНАЯ ФУНКЦИЯ КЛАССИФИКАЦИИ (принимает JSON-строку из Python)
std::string classify_request(const std::string& input_json_str) {
    // Парсим входящую JSON-строку
    auto input_json = json::parse(input_json_str);
    std::string user_text = input_json.value("message", "");

    // Токенизируем входящее сообщение пользователя
    std::vector<std::string> user_tokens = preprocess_and_tokenize(user_text);

    // Жесткие словари-маркеры для полного каталога услуг ТПУ (см. database/bz.json).
    // Ключи строго совпадают с названиями категорий в bz.json, чтобы Python-слою
    // не приходилось дополнительно приводить регистр/название (см. normalize_category
    // в services.py — там же оставлен алиасинг как страховка на случай расхождений).
    std::unordered_map<std::string, std::vector<std::string>> tpu_catalog = {
        {"Wi-Fi", {"интернет", "вайфай", "wifi", "tpu-student", "tpu-guest", "сеть", "подключиться", "eduroam", "едуроам", "роуминг"}},
        {"VPN", {"впн", "vpn", "anyconnect", "шлюз", "удаленка"}},
        {"Корпоративная почта", {"почта", "outlook", "аутлук", "письмо", "ящик", "mail", "spam", "спам", "imap", "smtp"}},
        {"ПО", {"виндовс", "windows", "офис", "office", "лицензия", "программа", "софт", "matlab", "python", "компилятор"}},
        {"Оборудование", {"компьютер", "монитор", "принтер", "мышка", "клавиатура", "ноутбук", "кабель", "проектор", "мфу", "мышь"}},
        {"Доступы к аккаунту", {"логин", "пароль", "аккаунт", "учетка", "войти", "авторизация"}},
        {"Успеваемость и Сессия", {"сессия", "экзамен", "зачет", "зачёт", "пересдача", "хвост", "долг", "брс", "аттестация"}},
        {"Стипендии и Выплаты", {"стипендия", "выплата", "выплаты", "гсс", "стипендию", "матпомощь"}},
        {"Переводы и Восстановление", {"перевод", "восстановление", "академ", "отчисление", "бюджет", "перевестись"}},
        {"Общежития", {"общежитие", "общага", "заселение", "комендант", "пропуск", "комната", "студгородок"}},
        {"Время работы", {"расписание", "деканат", "библиотека", "график", "часы", "режим", "нтб"}}
    };

    std::unordered_map<std::string, int> category_scores;

    // Алгоритмический матчинг слов
    for (const auto& token : user_tokens) {
        for (const auto& [category, keywords] : tpu_catalog) {
            for (const auto& keyword : keywords) {

                // Сценарий 1: Точное совпадение токена и ключевого слова
                if (token == keyword) {
                    category_scores[category] += 3; // Высокий приоритет за точное совпадение
                }
                // Сценарий 2: Поиск опечатки через Левенштейна (для слов длиннее 3 символов)
                else if (token.size() > 3 && keyword.size() > 3) {
                    if (get_levenshtein_distance(token, keyword) == 1) {
                        category_scores[category] += 2; // Чуть меньший балл за исправление опечатки
                    }
                }
            }
        }
    }

    // Ищем категорию с максимальным количеством набранных баллов
    std::string final_category = "unknown";
    int max_score = 0;

    for (const auto& [category, score] : category_scores) {
        if (score > max_score) {
            max_score = score;
            final_category = category;
        }
    }

    // Считаем условный процент уверенности (для ТЗ)
    int confidence = 0;
    if (max_score > 0) {
        // Простейшая хакатоновская метрика уверенности: от 50% до 100% в зависимости от баллов
        confidence = std::min(100, 50 + (max_score * 10));
    }

    // Формируем выходной JSON
    json response_json;
    response_json["category"] = final_category;
    response_json["confidence"] = confidence;

    // Возвращаем результат обратно в Python в виде JSON-строки
    return response_json.dump();
}

// 4. РЕГИСТРАЦИЯ МОДУЛЯ ДЛЯ PYBIND11
PYBIND11_MODULE(tpu_classifier, m) {
    m.doc() = "C++ Core Algorithm for TPU Helpdesk Classification";
    m.def("classify_request", &classify_request, "Classifies user message and returns a JSON string");
}
