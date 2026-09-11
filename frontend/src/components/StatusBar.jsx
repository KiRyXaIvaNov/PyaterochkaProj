export function StatusBar({ category, state, confidence }) {
  const stateLabels = {
    clarify: "Уточнение",
    clarification: "Уточнение",
    clarification: "Уточнение",
    solution: "Решение",
    finish: "Завершение",
    specialist: "Специалист",
  };

  return (
    <div className="flex items-center gap-4 px-4 py-2 bg-tpu-gray text-xs text-gray-700 border-b-2 border-tpu-gray">
      {category && (
        <span>
          Категория: <b>{category}</b>
        </span>
      )}
      {state && (
        <span>
          Статус: <b>{stateLabels[state] || state}</b>
        </span>
      )}
      {confidence !== null && confidence !== undefined && (
        <span>
          Уверенность: <b>{Math.round(confidence * 100)}%</b>
        </span>
      )}
    </div>
  );
}