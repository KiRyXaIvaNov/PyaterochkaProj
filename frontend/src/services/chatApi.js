const BASE_URL = "http://localhost:8000";

export async function sendMessage(email, text) {
    const res = await fetch(`${BASE_URL}/api/chat/send`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify({
            email,
            message: text,
        }),
    });

    if (!res.ok) {
        const error = await res.json().catch(() => ({}));

        throw new Error(
            error.detail || "Не удалось получить ответ"
        );
    }

    return res.json();
}

export async function getChatHistory(email) {
    const res = await fetch(
        `${BASE_URL}/api/chat/history?email=${encodeURIComponent(email)}`
    );

    if (!res.ok) {
        throw new Error("Не удалось загрузить историю чата");
    }

    return res.json();
}