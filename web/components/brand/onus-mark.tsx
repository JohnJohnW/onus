/** The Onus brand mark: a ring (the "O") enclosing a check — verified compliance.
 *  Single-colour; inherits `currentColor`, so set the colour with a text class. */
export function OnusMark({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 100 100"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
      aria-hidden="true"
    >
      <circle cx="50" cy="50" r="34" stroke="currentColor" strokeWidth="12" />
      <path
        d="M36 51 L46 61 L65 38"
        stroke="currentColor"
        strokeWidth="11"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}
