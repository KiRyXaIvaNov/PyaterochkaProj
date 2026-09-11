export function MessageBubble({ msg }) {
  const isUser = msg.role === "user";
  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"} mb-2`}>
      <div
        className={`max-w-[75%] px-4 py-2 rounded-2xl text-sm ${
          isUser
            ? "bg-tpu-green text-white rounded-br-sm"
            : "bg-tpu-gray text-gray-900 rounded-bl-sm"
        }`}
      >
        {msg.text}
      </div>
    </div>
  );
}