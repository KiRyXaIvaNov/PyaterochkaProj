import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { getCurrentUser, logout } from "../services/auth";
import { getTickets, updateTicket } from "../services/tickets";

const STATUS_LABELS = {
  open: "Новое",
  in_progress: "В работе",
  closed: "Закрыто",
  "Решено ботом": "Решено ботом",
  "Требуется уточнение": "Требуется уточнение",
};

const STATUS_COLORS = {
  open: "bg-red-100 text-red-700",
  in_progress: "bg-yellow-100 text-yellow-700",
  closed: "bg-green-100 text-green-700",
  "Решено ботом": "bg-green-100 text-green-700",
  "Требуется уточнение": "bg-yellow-100 text-yellow-700",
};

export function AdminPage() {
  const navigate = useNavigate();
  const user = getCurrentUser();
  const [tickets, setTickets] = useState([]);
  const [selected, setSelected] = useState(null);
  const [reply, setReply] = useState("");

  const loadTickets = async () => {
    try {
      setTickets(await getTickets());
    } catch (e) {
      console.error("Не удалось загрузить обращения:", e);
    }
  };

  useEffect(() => { loadTickets(); }, []);

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  const handleSendReply = async () => {
    if (!reply.trim() || !selected) return;
    try {
      await updateTicket(selected.id, { adminReply: reply });
      await loadTickets();
      setReply("");
      setSelected(null);
    } catch (e) {
      console.error("Не удалось отправить ответ:", e);
    }
  };

  return (
    <div className="min-h-screen bg-tpu-white">
      <div className="flex items-center justify-between px-6 py-3 bg-tpu-green text-white">
        <div className="font-semibold">Админ-панель ТПУ</div>
        <div className="flex items-center gap-3 text-sm">
          <span>{user?.email}</span>
          <button onClick={handleLogout} className="bg-white text-tpu-green px-3 py-1 rounded-lg text-xs font-medium">Выйти</button>
        </div>
      </div>

      <div className="p-6 max-w-6xl mx-auto">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-xl font-bold text-tpu-green">Обращения пользователей</h2>
          <button onClick={loadTickets} className="px-3 py-2 border-2 border-tpu-gray rounded-lg text-sm">Обновить</button>
        </div>

        {tickets.length === 0 ? (
          <div className="flex items-center justify-center min-h-[40vh] border-2 border-dashed border-tpu-gray rounded-xl">
            <p className="text-gray-500 text-center">Пока нет обращений. Они появятся здесь после общения пользователей с помощником.</p>
          </div>
        ) : (
          <div className="border-2 border-tpu-gray rounded-xl overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-tpu-gray text-gray-800">
                <tr>
                  <th className="text-left px-4 py-2">Пользователь</th>
                  <th className="text-left px-4 py-2">Категория</th>
                  <th className="text-left px-4 py-2">Сообщение</th>
                  <th className="text-left px-4 py-2">Уверенность</th>
                  <th className="text-left px-4 py-2">Статус</th>
                  <th className="px-4 py-2"></th>
                </tr>
              </thead>
              <tbody>
                {tickets.map((t) => (
                  <tr key={t.id} className="border-t border-tpu-gray">
                    <td className="px-4 py-2">{t.email}</td>
                    <td className="px-4 py-2">{t.category}</td>
                    <td className="px-4 py-2 max-w-xs truncate">{t.message}</td>
                    <td className="px-4 py-2">{t.confidence != null ? `${Math.round(t.confidence * 100)}%` : "—"}</td>
                    <td className="px-4 py-2"><span className={`px-2 py-1 rounded-full text-xs ${STATUS_COLORS[t.status] || "bg-gray-100 text-gray-700"}`}>{STATUS_LABELS[t.status] || t.status}</span></td>
                    <td className="px-4 py-2"><button onClick={() => setSelected(t)} className="text-tpu-green underline text-xs">Открыть</button></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {selected && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-lg w-full p-6 border-2 border-tpu-gray">
            <h3 className="text-lg font-bold text-tpu-green mb-2">Обращение от {selected.email}</h3>
            <p className="text-sm text-gray-700 mb-1"><b>Категория:</b> {selected.category}</p>
            <p className="text-sm text-gray-700 mb-1"><b>Дата:</b> {selected.created_at || "—"}</p>
            <p className="text-sm text-gray-700 mb-4"><b>Сообщение:</b> {selected.message}</p>
            {selected.admin_reply && <p className="text-sm text-gray-700 mb-4 bg-green-50 border border-tpu-green rounded-lg p-2"><b>Ваш ответ:</b> {selected.admin_reply}</p>}
            <textarea value={reply} onChange={(e) => setReply(e.target.value)} placeholder="Введите ответ пользователю..." rows={4} className="w-full border-2 border-tpu-gray rounded-lg p-3 text-sm outline-none focus:border-tpu-green mb-4" />
            <div className="flex justify-end gap-2">
              <button onClick={() => { setSelected(null); setReply(""); }} className="px-4 py-2 rounded-lg border-2 border-tpu-gray text-sm">Отмена</button>
              <button onClick={handleSendReply} className="px-4 py-2 rounded-lg bg-tpu-green text-white text-sm">Ответить и закрыть</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
