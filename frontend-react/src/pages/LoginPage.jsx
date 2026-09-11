import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { login } from "../services/auth";

export function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const navigate = useNavigate();

  const handleSubmit = (e) => {
    e.preventDefault();
    setError("");

    if (!email.includes("@")) {
      setError("Введите корректную почту ТПУ");
      return;
    }

    if (password.length < 3) {
      setError("Пароль слишком короткий");
      return;
    }

    const user = login(email, password);

    if (user.role === "admin") {
      navigate("/admin");
    } else {
      navigate("/chat");
    }
  };

  return (
    <div className="min-h-screen bg-tpu-white flex items-center justify-center px-4">
      <form
        onSubmit={handleSubmit}
        className="w-full max-w-md bg-white border-2 border-tpu-gray rounded-2xl p-8"
      >
        <div className="text-center mb-8">
          <img
            src="/tpu-logo.png"
            alt="ТПУ"
            className="w-20 h-20 mx-auto mb-4 object-contain"
/>
          <h1 className="text-2xl font-bold text-tpu-green">
            Техподдержка ТПУ
          </h1>
          <p className="text-sm text-gray-500 mt-1">
            Войдите, чтобы продолжить
          </p>
        </div>

        <label className="block mb-4">
          <span className="text-sm text-gray-700">Почта ТПУ</span>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="ivanov@tpu.ru"
            className="mt-1 w-full border-2 border-tpu-gray rounded-lg px-4 py-2 outline-none focus:border-tpu-green"
          />
        </label>

        <label className="block mb-6">
          <span className="text-sm text-gray-700">Пароль</span>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="••••••"
            className="mt-1 w-full border-2 border-tpu-gray rounded-lg px-4 py-2 outline-none focus:border-tpu-green"
          />
        </label>

        {error && (
          <div className="mb-4 text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
            {error}
          </div>
        )}

        <button
          type="submit"
          className="w-full bg-tpu-green text-white py-2.5 rounded-lg font-medium hover:opacity-90 transition"
        >
          Войти
        </button>

        
      </form>
    </div>
  );
}