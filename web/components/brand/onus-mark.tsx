/** The Onus brand mark: a circular seal with a diamond aperture — a precise
 *  compliance stamp. Single-colour; inherits `currentColor`, so set the colour
 *  with a text class (e.g. text-neutral-50 on the dark chrome). */
export function OnusMark({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 100 100"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
      aria-hidden="true"
    >
      <path
        fill="currentColor"
        fillRule="evenodd"
        d="M50 14 A36 36 0 1 0 50 86 A36 36 0 1 0 50 14 Z M50 30 L70 50 L50 70 L30 50 Z"
      />
    </svg>
  );
}
