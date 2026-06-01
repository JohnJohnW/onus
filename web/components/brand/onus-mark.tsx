/** The Onus brand mark: a solid ring (the "O") over a chevron — a compliance seal.
 *  Single-colour; inherits `currentColor`, so set the colour with a text class. */
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
        d="M50 10 A26 26 0 1 0 50 62 A26 26 0 1 0 50 10 Z M50 21.5 A14.5 14.5 0 1 0 50 50.5 A14.5 14.5 0 1 0 50 21.5 Z"
      />
      <path fill="currentColor" d="M28 66 L50 79 L72 66 L72 76 L50 89 L28 76 Z" />
    </svg>
  );
}
