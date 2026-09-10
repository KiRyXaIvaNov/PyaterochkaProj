import { mockSendMessage } from "./mockChat";

const USE_MOCK = true; // поменяешь на false, когда бэкенд будет готов
const BASE_URL = "http://localhost:8000";

export async function sendMessage(sessionId, text) {
  if (USE_MOCK) return mockSendMessage(sessionId, text);

  const res = await fetch(`${BASE_URL}/api/message`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ sessionId, text }),
  });
  return res.json();
}