// Simple chalk-style SVG sketches that change per lecture segment.
// Kept intentionally hand-drawn / sketchy to match the "teacher at a board" feel.
const CHALK = "#f4efe1";
const CHALK_DIM = "#9db8a8";

function VectorsSvg() {
  return (
    <svg viewBox="0 0 220 160" width="100%" height="100%">
      <line x1="20" y1="140" x2="200" y2="140" stroke={CHALK_DIM} strokeWidth="1.5" />
      <line x1="30" y1="150" x2="30" y2="20" stroke={CHALK_DIM} strokeWidth="1.5" />
      <line x1="30" y1="140" x2="130" y2="50" stroke={CHALK} strokeWidth="3" markerEnd="url(#arrow)" />
      <line x1="30" y1="140" x2="170" y2="110" stroke={CHALK} strokeWidth="3" markerEnd="url(#arrow)" />
      <text x="135" y="45" fill={CHALK} fontSize="16" fontStyle="italic">A</text>
      <text x="175" y="115" fill={CHALK} fontSize="16" fontStyle="italic">B</text>
      <defs>
        <marker id="arrow" markerWidth="8" markerHeight="8" refX="4" refY="4" orient="auto">
          <path d="M0,0 L8,4 L0,8 Z" fill={CHALK} />
        </marker>
      </defs>
    </svg>
  );
}

function RightHandRuleSvg() {
  return (
    <svg viewBox="0 0 220 160" width="100%" height="100%">
      <ellipse cx="110" cy="90" rx="55" ry="30" fill="none" stroke={CHALK_DIM} strokeDasharray="4 4" />
      <line x1="55" y1="90" x2="165" y2="90" stroke={CHALK} strokeWidth="3" markerEnd="url(#arrow2)" />
      <line x1="110" y1="90" x2="110" y2="30" stroke={CHALK} strokeWidth="3" markerEnd="url(#arrow2)" />
      <circle cx="110" cy="90" r="4" fill={CHALK} />
      <text x="35" y="95" fill={CHALK} fontSize="14">curl</text>
      <text x="118" y="28" fill={CHALK} fontSize="16" fontStyle="italic">A×B</text>
      <defs>
        <marker id="arrow2" markerWidth="8" markerHeight="8" refX="4" refY="4" orient="auto">
          <path d="M0,0 L8,4 L0,8 Z" fill={CHALK} />
        </marker>
      </defs>
    </svg>
  );
}

function FormulaSvg({ label = "|A×B| = |A||B| sinθ" }) {
  return (
    <svg viewBox="0 0 220 160" width="100%" height="100%">
      <text x="20" y="85" fill={CHALK} fontSize="20" fontFamily="monospace">
        {label}
      </text>
      <path d="M20,95 h180" stroke={CHALK_DIM} strokeWidth="1" strokeDasharray="3 5" />
    </svg>
  );
}

function ApplicationsSvg() {
  return (
    <svg viewBox="0 0 220 160" width="100%" height="100%">
      <circle cx="60" cy="80" r="26" fill="none" stroke={CHALK} strokeWidth="2.5" />
      <line x1="60" y1="80" x2="60" y2="35" stroke={CHALK} strokeWidth="2.5" markerEnd="url(#arrow3)" />
      <text x="35" y="120" fill={CHALK_DIM} fontSize="11">Torque</text>

      <line x1="150" y1="120" x2="150" y2="40" stroke={CHALK} strokeWidth="2.5" markerEnd="url(#arrow3)" />
      <path d="M130,110 q20,-40 40,0" stroke={CHALK_DIM} strokeWidth="1.5" fill="none" />
      <text x="118" y="135" fill={CHALK_DIM} fontSize="11">Magnetic force</text>
      <defs>
        <marker id="arrow3" markerWidth="8" markerHeight="8" refX="4" refY="4" orient="auto">
          <path d="M0,0 L8,4 L0,8 Z" fill={CHALK} />
        </marker>
      </defs>
    </svg>
  );
}

function GenericSvg() {
  return (
    <svg viewBox="0 0 220 160" width="100%" height="100%">
      <circle cx="110" cy="80" r="6" fill={CHALK} />
      <path
        d="M40,80 C60,40 90,120 110,80 S160,40 180,80"
        fill="none"
        stroke={CHALK}
        strokeWidth="2.5"
      />
    </svg>
  );
}

const MAP = {
  "vectors-2d": VectorsSvg,
  "right-hand-rule": RightHandRuleSvg,
  "magnitude-formula": FormulaSvg,
  applications: ApplicationsSvg,
  graph: FormulaSvg,
  diagram: VectorsSvg,
  timeline: ApplicationsSvg,
  molecule: RightHandRuleSvg,
  circuit: GenericSvg,
};

export default function LectureVisual({ kind }) {
  const Comp = MAP[kind] || GenericSvg;
  return (
    <div className="lecture-visual">
      <Comp />
    </div>
  );
}
