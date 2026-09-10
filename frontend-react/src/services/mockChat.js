const sessions = {}; // хранит шаг для каждой сессии отдельно

export async function mockSendMessage(sessionId, text) {
  await new Promise((r) => setTimeout(r, 600));
    // Если пользователь уже запросил специалиста — отвечаем один раз
if (text === "Нет, нужен специалист") {
  return {
    sessionId,
    reply: "Я передал ваше обращение специалисту. Ожидайте ответа в этом чате.",
    category: sessions[sessionId]?.category || null,
    state: "specialist",
    options: null,
    steps: null,
    confidence: 0.9,
  };
}

// Если пользователь сказал "Да, спасибо" — завершаем
if (text === "Да, спасибо") {
  return {
    sessionId,
    reply: "Рад был помочь! Если появятся ещё вопросы — обращайтесь.",
    category: sessions[sessionId]?.category || null,
    state: "finish",
    options: null,
    steps: null,
    confidence: 0.95,
  };
}
  // Если сессия новая — создаём счётчик
  if (!sessions[sessionId]) {
    sessions[sessionId] = { step: 0, category: null };
  }

  const s = sessions[sessionId];

  // Первый шаг — классификация и уточнение
  if (s.step === 0) {
    s.step = 1;
    s.category = detectCategory(text);

    return {
      sessionId,
      reply: "Уточните, пожалуйста: проблема в кампусе или в общежитии?",
      category: s.category,
      state: "clarify",
      options: ["В кампусе", "В общежитии"],
      steps: null,
      confidence: 0.7,
    };
  }

  // Второй шаг — решение
  if (s.step === 1) {
    s.step = 2;
    return {
      sessionId,
      reply: "Попробуйте выполнить следующие шаги:",
      category: s.category,
      state: "solution",
      options: null,
      steps: getSolutionSteps(s.category),
      confidence: 0.85,
    };
  }

  // Третий шаг — завершение
  s.step = 3;
  return {
    sessionId,
    reply: "Удалось ли решить проблему?",
    category: s.category,
    state: "finish",
    options: ["Да, спасибо", "Нет, нужен специалист"],
    steps: null,
    confidence: 0.9,
  };
}

function detectCategory(text) {
  const lower = text.toLowerCase();
  if (lower.includes("wi-fi") || lower.includes("wifi") || lower.includes("вайфай") || lower.includes("интернет")) {
    return "Wi-Fi и интернет";
  }
  if (lower.includes("vpn")) return "VPN";
  if (lower.includes("пароль") || lower.includes("логин") || lower.includes("кабинет")) return "Доступы";
  if (lower.includes("почт") || lower.includes("письм")) return "Корпоративная почта";
  if (lower.includes("розетк") || lower.includes("кран") || lower.includes("душ") || lower.includes("батаре")) return "Общежитие: инфраструктура";
  return "Другое";
}

function getSolutionSteps(category) {
  if (category === "Wi-Fi и интернет") {
    return [
      "Проверьте, включён ли Wi-Fi на устройстве",
      "Забудьте сеть и подключитесь заново",
      "Перезагрузите устройство",
      "Если не помогло — обратитесь к специалисту",
    ];
  }
  if (category === "VPN") {
    return [
      "Проверьте подключение к интернету",
      "Откройте приложение VPN",
      "Перезапустите подключение",
      "Если проблема сохраняется — обратитесь к специалисту",
    ];
  }
  if (category === "Доступы") {
    return [
      "Проверьте правильность ввода логина",
      "Нажмите «Забыли пароль?»",
      "Следуйте инструкции в письме",
      "Если письмо не пришло — обратитесь к специалисту",
    ];
  }
  if (category === "Общежитие: инфраструктура") {
    return [
      "Уточните номер комнаты и этажа",
      "Сообщите коменданту о проблеме",
      "Дождитесь прихода специалиста",
    ];
  }
  return ["Опишите проблему подробнее", "Обратитесь к специалисту"];
}