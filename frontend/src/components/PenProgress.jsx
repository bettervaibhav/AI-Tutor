// A progress indicator styled as a hand-drawn pen underline instead of a
// generic flat bar — ties back to the notebook / marking-pen concept.
export default function PenProgress({ pct = 0, color = "var(--pen-red)" }) {
  const clamped = Math.max(0, Math.min(100, pct));
  return (
    <svg className="pen-progress" viewBox="0 0 200 10" preserveAspectRatio="none">
      <path
        d="M2,6 Q15,2 28,6 T54,6 T80,6 T106,6 T132,6 T158,6 T184,6 T198,6"
        pathLength="100"
      />
      <path
        className="fill"
        d="M2,6 Q15,2 28,6 T54,6 T80,6 T106,6 T132,6 T158,6 T184,6 T198,6"
        pathLength="100"
        style={{
          stroke: color,
          strokeDasharray: 100,
          strokeDashoffset: 100 - clamped,
        }}
      />
    </svg>
  );
}
