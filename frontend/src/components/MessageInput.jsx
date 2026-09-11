import { useState } from "react";

export function MessageInput({ onSend, disabled }) {
  const [text, setText] = useState("");

  const handleSend = () => {
    if (!text.trim() || disabled) return;
    onSend(text.trim());
    setText("");
  };

  return (
    <div className="flex gap-2 p-3 border-t-2 border-tpu-gray bg-white">
      <input
        className="flex-1 border-2 border-tpu-gray rounded-full px-4 py-2 outline-none focus:border-tpu-green"
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={(e) => e.key === "Enter" && handleSend()}
        placeholder="Опишите проблему..."
        disabled={disabled}
      />
      <button
        onClick={handleSend}
        disabled={disabled}
        className="bg-tpu-green text-white px-5 py-2 rounded-full disabled:opacity-50"
      >
        Отправить
      </button>
    </div>
  );
}