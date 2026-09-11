export function QuickOptions({ options, onSelect }) {
  return (
    <div className="flex flex-wrap gap-2 mt-2">
      {options.map((opt) => (
        <button
          key={opt}
          onClick={() => onSelect(opt)}
          className="border-2 border-tpu-green text-tpu-green px-4 py-1 rounded-full text-sm hover:bg-green-50"
        >
          {opt}
        </button>
      ))}
    </div>
  );
}