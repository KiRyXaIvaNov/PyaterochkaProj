import { getTickets } from "../services/tickets";
import { saveTicket } from "../services/tickets";
import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { getCurrentUser, logout } from "../services/auth";
import { sendMessage } from "../services/chatApi";
import { MessageBubble } from "../components/MessageBubble";
import { MessageInput } from "../components/MessageInput";
import { QuickOptions } from "../components/QuickOptions";
import { SolutionSteps } from "../components/SolutionSteps";
import { StatusBar } from "../components/StatusBar";

export function ChatPage() {
  const navigate = useNavigate();
  const user = getCurrentUser();

  const [sessionId] = useState(() => crypto.randomUUID());
  const [messages, setMessages] = useState([
    {
      id: crypto.randomUUID(),
      role: "assistant",
      text: "Здравствуйте! Опишите вашу проблему, и я постараюсь помочь.",
      timestamp: Date.now(),
    },
  ]);
  const [category, setCategory] = useState(null);
  const [state, setState] = useState(null);
  const [options, setOptions] = useState(null);
  const [steps, setSteps] = useState(null);
  const [confidence, setConfidence] = useState(null);
  const [isLoading, setIsLoading] = useState(false);

  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, steps, options]);
  useEffect(() => {
    // Проверяем только если пользователь уже запросил специалиста
    if (state !== "specialist" && state !== "finish") return;

    const interval = setInterval(() => {
      const tickets = getTickets();
      const myTicket = tickets.find((t) => t.id === sessionId);

      if (myTicket?.adminReply) {
        const alreadyShown = messages.some(
          (m) => m.text === `Ответ специалиста: ${myTicket.adminReply}`
        );

        if (!alreadyShown) {
          setMessages((prev) => [
            ...prev,
            {
              id: crypto.randomUUID(),
              role: "assistant",
              text: `Ответ специалиста: ${myTicket.adminReply}`,
              timestamp: Date.now(),
            },
          ]);
          setState("specialist");
        }
      }
    }, 3000);

    return () => clearInterval(interval);
  }, [state, sessionId, messages]);
  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  const handleSend = async (text) => {
    setMessages((prev) => [
      ...prev,
      {
        id: crypto.randomUUID(),
        role: "user",
        text,
        timestamp: Date.now(),
      },
    ]);
    setIsLoading(true);
    setOptions(null);
    setSteps(null);

    try {
      const res = await sendMessage(sessionId, text);
      setMessages((prev) => [
        ...prev,
        {
          id: crypto.randomUUID(),
          role: "assistant",
          text: res.reply,
          timestamp: Date.now(),
        },
      ]);
      setCategory(res.category);
      setState(res.state);
      setOptions(res.options);
      setSteps(res.steps);
      setConfidence(res.confidence);
      if (res.state === "specialist") {
        saveTicket({
          id: sessionId,
          email: user?.email || "unknown@tpu.ru",
          category: res.category || "Не определена",
          message: messages
        .filter((m) => m.role === "user")
        .map((m) => m.text)
        .join(" | "),
        status: "open",
        confidence: res.confidence,
        createdAt: new Date().toLocaleString("ru-RU"),
        });
      }
    } catch (e) {
      setMessages((prev) => [
        ...prev,
        {
          id: crypto.randomUUID(),
          role: "assistant",
          text: "Не удалось получить ответ. Попробуйте ещё раз.",
          timestamp: Date.now(),
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-tpu-white flex flex-col">
      {/* Шапка */}
      <div className="flex items-center justify-between px-6 py-3 bg-tpu-green text-white">
        <div className="font-semibold">Техподдержка ТПУ</div>
        <div className="flex items-center gap-3 text-sm">
          <span>{user?.email}</span>
          <button
            onClick={handleLogout}
            className="bg-white text-tpu-green px-3 py-1 rounded-lg text-xs font-medium"
          >
            Выйти
          </button>
        </div>
      </div>

      {/* Статусная строка */}
      <StatusBar category={category} state={state} confidence={confidence} />

      {/* История сообщений */}
      <div className="flex-1 overflow-y-auto p-4 max-w-2xl w-full mx-auto">
        {messages.map((m) => (
          <MessageBubble key={m.id} msg={m} />
        ))}

        {isLoading && (
          <div className="text-gray-400 text-sm mb-2">Печатает…</div>
        )}

        {steps && !isLoading && <SolutionSteps steps={steps} />}

        {options && !isLoading && (
          <QuickOptions options={options} onSelect={handleSend} />
        )}

        <div ref={bottomRef} />
      </div>

      {/* Поле ввода */}
      <div className="max-w-2xl w-full mx-auto">
        <MessageInput onSend={handleSend} disabled={isLoading} />
      </div>
    </div>
  );
}