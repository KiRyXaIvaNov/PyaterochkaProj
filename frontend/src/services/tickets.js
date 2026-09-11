const BASE_URL = "http://localhost:8000";

export async function getTickets() {
  const res = await fetch(`${BASE_URL}/api/admin/tickets`);
  if (!res.ok) throw new Error("Не удалось загрузить обращения");
  return res.json();
}

export async function updateTicket(id, changes) {
  if (changes.adminReply) {
    const res = await fetch(`${BASE_URL}/api/admin/tickets/${id}/reply`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ reply: changes.adminReply }),
    });
    if (!res.ok) throw new Error("Не удалось отправить ответ");
    return (await res.json()).ticket;
  }

  if (changes.status) {
    const res = await fetch(`${BASE_URL}/api/admin/tickets/${id}?status=${encodeURIComponent(changes.status)}`, { method: "PATCH" });
    if (!res.ok) throw new Error("Не удалось изменить статус");
    return (await res.json()).ticket;
  }
}
