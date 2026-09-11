export function SolutionSteps({ steps }) {
  return (
    <div className="my-3 space-y-2">
      {steps.map((s, i) => (
        <div
          key={i}
          className="flex gap-3 items-start bg-green-50 border-2 border-tpu-green rounded-lg p-3"
        >
          <div className="w-6 h-6 rounded-full bg-tpu-green text-white text-xs flex items-center justify-center flex-shrink-0">
            {i + 1}
          </div>
          <div className="text-sm text-gray-800">{s}</div>
        </div>
      ))}
    </div>
  );
}