const KEY = "tpu_user";

export function login(email, password) {
  // Пока бэкенда нет — определяем роль по почте.
  // Позже заменим на POST /api/auth/login
  let role = "user";
  if (email.startsWith("admin@") || email === "admin@tpu.ru") {
    role = "admin";
  }

  const user = { email, role, token: "mock-token-" + Date.now() };
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