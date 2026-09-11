import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { getCurrentUser, logout } from "../services/auth";
import { sendMessage, getChatHistory } from "../services/chatApi";
import { MessageBubble } from "../components/MessageBubble";
import { MessageInput } from "../components/MessageInput";
import { QuickOptions } from "../components/QuickOptions";
import { SolutionSteps } from "../components/SolutionSteps";
import { StatusBar } from "../components/StatusBar";

export function ChatPage() {
  const navigate = useNavigate();
  const user = getCurrentUser();
  const [messages, setMessages] = useState([
    { id: crypto.randomUUID(), role: "assistant", text: "Здравствуйте! Опишите вашу проблему, и я постараюсь помочь.", timestamp: Date.now() },
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
    if (!user?.email) return;
    getChatHistory(user.email)
      .then((history) => {
        if (history.length) {
          setMessages(history.map((m) => ({
            id: String(m.id),
            role: m.author === "user" ? "user" : "assistant",
            text: m.text,
            timestamp: Date.now(),
          })));
        }
      })
      .catch((e) => console.error("Не удалось загрузить историю:", e));
  }, [user?.email]);

  // Проверяем историю, чтобы ответ специалиста появился без перезагрузки.
  useEffect(() => {
    if (!user?.email || state !== "specialist") return;
    const timer = setInterval(async () => {
      try {
        const history = await getChatHistory(user.email);
        setMessages(history.map((m) => ({
          id: String(m.id),
          role: m.author === "user" ? "user" : "assistant",
          text: m.text,
          timestamp: Date.now(),
        })));
      } catch (e) {
        console.error(e);
      }
    }, 3000);
    return () => clearInterval(timer);
  }, [user?.email, state]);

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  const handleSend = async (text) => {
    setMessages((prev) => [...prev, { id: crypto.randomUUID(), role: "user", text, timestamp: Date.now() }]);
    setIsLoading(true);
    setOptions(null);
    setSteps(null);

    try {
      const res = await sendMessage(user.email, text);
      setMessages((prev) => [...prev, { id: crypto.randomUUID(), role: "assistant", text: res.reply, timestamp: Date.now() }]);
      setCategory(res.category);
      setState(res.state);
      setOptions(res.options);
      setSteps(res.steps);
      setConfidence(res.confidence);
    } catch (e) {
      setMessages((prev) => [...prev, { id: crypto.randomUUID(), role: "assistant", text: "Не удалось получить ответ. Проверьте, запущен ли backend, и попробуйте ещё раз.", timestamp: Date.now() }]);
      console.error(e);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-tpu-white flex flex-col">
      <div className="flex items-center justify-between px-6 py-3 bg-tpu-green text-white">
        <div className="font-semibold">Техподдержка ТПУ</div>
        <div className="flex items-center gap-3 text-sm">
          <span>{user?.email}</span>
          <button onClick={handleLogout} className="bg-white text-tpu-green px-3 py-1 rounded-lg text-xs font-medium">Выйти</button>
        </div>
      </div>

      <StatusBar category={category} state={state} confidence={confidence} />

      <div className="flex-1 overflow-y-auto p-4 max-w-2xl w-full mx-auto">
        {messages.map((m) => <MessageBubble key={m.id} msg={m} />)}
        {isLoading && <div className="text-gray-400 text-sm mb-2">Печатает…</div>}
        {steps && !isLoading && <SolutionSteps steps={steps} />}
        {options && !isLoading && <QuickOptions options={options} onSelect={handleSend} />}
        <div ref={bottomRef} />
      </div>

      <div className="max-w-2xl w-full mx-auto">
        <MessageInput onSend={handleSend} disabled={isLoading} />
      </div>
    </div>
  );
}
