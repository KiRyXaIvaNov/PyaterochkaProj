const KEY = "tpu_tickets";

export function getTickets() {
  const raw = localStorage.getItem(KEY);
  return raw ? JSON.parse(raw) : [];
}

export function saveTicket(ticket) {
  const all = getTickets();
  // Не создавать дубликат, если уже есть с таким id
  const exists = all.find((t) => t.id === ticket.id);
  if (exists) return;
  all.push(ticket);
  localStorage.setItem(KEY, JSON.stringify(all));
}

export function updateTicket(id, changes) {
  const all = getTickets();
  const updated = all.map((t) => (t.id === id ? { ...t, ...changes } : t));
  localStorage.setItem(KEY, JSON.stringify(updated));
}