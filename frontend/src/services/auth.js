const KEY = "tpu_user";

const BASE_URL = "http://localhost:8000";

export async function login(email, password) {
    const res = await fetch(`${BASE_URL}/api/auth/login`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify({
            email,
            password,
        }),
    });

    if (!res.ok) {
        const error = await res.json().catch(() => ({}));

        throw new Error(
            error.detail || "Не удалось выполнить вход"
        );
    }

    const data = await res.json();

    const user = {
        email: data.user.email,
        role: data.user.role,
    };

    localStorage.setItem(KEY, JSON.stringify(user));

    return user;
}

export function logout() {
    localStorage.removeItem(KEY);
}

export function getCurrentUser() {
    const raw = localStorage.getItem(KEY);

    return raw ? JSON.parse(raw) : null;
}