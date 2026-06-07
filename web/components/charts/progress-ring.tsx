// Dependency-free progress ring (single SVG circle with stroke-dasharray). Colour shifts
// red -> amber -> emerald with completion. Used for compliance readiness on the dashboard.
export function ProgressRing({
  percent,
  size = 76,
  stroke = 8,
  label,
}: {
  percent: number;
  size?: number;
  stroke?: number;
  label?: string;
}) {
  const pct = Math.max(0, Math.min(100, percent));
  const r = (size - stroke) / 2;
  const circumference = 2 * Math.PI * r;
  const offset = circumference * (1 - pct / 100);
  const color = pct >= 100 ? "#059669" : pct >= 50 ? "#d97706" : "#dc2626";
  return (
    <div className="relative shrink-0" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90" aria-hidden>
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="#262626" strokeWidth={stroke} />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          stroke={color}
          strokeWidth={stroke}
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          strokeLinecap="round"
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-sm font-semibold text-neutral-100">{pct}%</span>
        {label && <span className="text-[10px] uppercase tracking-wide text-neutral-500">{label}</span>}
      </div>
    </div>
  );
}
