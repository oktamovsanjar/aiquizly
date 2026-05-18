// Lightweight hand-rolled SVG charts — line and bar.
// Tooltip-on-hover, axis-y on left, sparse x-axis labels at bottom.

const range = (n) => Array.from({ length: n }, (_, i) => i);

function useChartDims(ref) {
  const [w, setW] = React.useState(600);
  React.useEffect(() => {
    if (!ref.current) return;
    const ro = new ResizeObserver(entries => {
      for (const e of entries) setW(Math.max(120, Math.floor(e.contentRect.width)));
    });
    ro.observe(ref.current);
    return () => ro.disconnect();
  }, [ref]);
  return w;
}

function niceMax(max) {
  if (max <= 0) return 10;
  const pow = Math.pow(10, Math.floor(Math.log10(max)));
  const norm = max / pow;
  let nice;
  if (norm <= 1) nice = 1;
  else if (norm <= 2) nice = 2;
  else if (norm <= 5) nice = 5;
  else nice = 10;
  return nice * pow;
}

const LineChart = ({ data, height = 240, series, yFormatter = (n) => n }) => {
  // data: [{ date, ...keys }], series: [{ key, label, color, fillId }]
  const wrapRef = React.useRef(null);
  const w = useChartDims(wrapRef);
  const padL = 44, padR = 12, padT = 12, padB = 28;
  const innerW = Math.max(40, w - padL - padR);
  const innerH = height - padT - padB;
  const n = data.length;
  const maxV = niceMax(Math.max(1, ...data.flatMap(d => series.map(s => d[s.key] || 0))));
  const xAt = (i) => padL + (n <= 1 ? innerW / 2 : (i * innerW) / (n - 1));
  const yAt = (v) => padT + innerH - (v / maxV) * innerH;

  // y ticks
  const ticks = 4;
  const tickVals = range(ticks + 1).map(i => (maxV * i) / ticks);

  // hover
  const [hover, setHover] = React.useState(null);

  const onMove = (e) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const rel = Math.max(0, Math.min(innerW, x - padL));
    const i = Math.round((rel / innerW) * (n - 1));
    setHover({ i, x: xAt(i) });
  };

  return (
    <div ref={wrapRef} className="w-full relative">
      <svg width={w} height={height} className="block" onMouseMove={onMove} onMouseLeave={() => setHover(null)}>
        {/* y grid + labels */}
        {tickVals.map((v, idx) => (
          <g key={idx}>
            <line x1={padL} x2={w - padR} y1={yAt(v)} y2={yAt(v)} stroke="rgb(244 244 245)" />
            <text x={padL - 8} y={yAt(v) + 4} textAnchor="end" className="fill-zinc-400 text-[10px] tnum">
              {yFormatter(Math.round(v))}
            </text>
          </g>
        ))}

        {/* x labels - first, middle, last (and a couple in between) */}
        {[0, Math.floor(n / 3), Math.floor((2 * n) / 3), n - 1].filter((v, i, a) => a.indexOf(v) === i).map((i) => (
          <text key={i} x={xAt(i)} y={height - 8} textAnchor="middle" className="fill-zinc-400 text-[10px]">
            {formatDateShort(data[i].date)}
          </text>
        ))}

        {/* defs for area fill */}
        <defs>
          {series.map((s) => (
            <linearGradient key={s.key} id={`grad-${s.key}`} x1="0" x2="0" y1="0" y2="1">
              <stop offset="0%" stopColor={s.color} stopOpacity="0.18" />
              <stop offset="100%" stopColor={s.color} stopOpacity="0" />
            </linearGradient>
          ))}
        </defs>

        {/* area + line per series */}
        {series.map((s) => {
          const pts = data.map((d, i) => `${xAt(i)},${yAt(d[s.key] || 0)}`).join(' ');
          const area = `${padL},${padT + innerH} ${pts} ${padL + innerW},${padT + innerH}`;
          return (
            <g key={s.key}>
              <polygon points={area} fill={`url(#grad-${s.key})`} />
              <polyline points={pts} fill="none" stroke={s.color} strokeWidth="2" strokeLinejoin="round" strokeLinecap="round" />
            </g>
          );
        })}

        {/* hover crosshair + dots */}
        {hover && (
          <g>
            <line x1={hover.x} x2={hover.x} y1={padT} y2={padT + innerH} stroke="rgb(212 212 216)" strokeDasharray="3 3" />
            {series.map((s) => (
              <circle key={s.key} cx={hover.x} cy={yAt(data[hover.i][s.key] || 0)} r="4" fill="white" stroke={s.color} strokeWidth="2" />
            ))}
          </g>
        )}
      </svg>

      {/* legend */}
      <div className="absolute top-0 right-0 flex items-center gap-3 text-xs text-zinc-600">
        {series.map((s) => (
          <div key={s.key} className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-sm" style={{ background: s.color }} />
            {s.label}
          </div>
        ))}
      </div>

      {/* tooltip */}
      {hover && (
        <div className="pointer-events-none absolute bg-white border border-zinc-200 shadow-pop rounded-md px-3 py-2 text-xs"
             style={{ left: Math.min(w - 180, Math.max(0, hover.x + 8)), top: 8 }}>
          <div className="text-zinc-500 mb-1">{formatDate(data[hover.i].date)}</div>
          {series.map((s) => (
            <div key={s.key} className="flex items-center justify-between gap-4 tnum">
              <span className="flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-sm" style={{ background: s.color }} />
                <span className="text-zinc-600">{s.label}</span>
              </span>
              <span className="font-medium text-zinc-900">{yFormatter(data[hover.i][s.key] || 0)}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

const BarChart = ({ data, height = 240, valueKey, color = 'rgb(24 24 27)', yFormatter = (n) => n, tooltipFormatter }) => {
  const wrapRef = React.useRef(null);
  const w = useChartDims(wrapRef);
  const padL = 56, padR = 12, padT = 12, padB = 28;
  const innerW = Math.max(40, w - padL - padR);
  const innerH = height - padT - padB;
  const n = data.length;
  const maxV = niceMax(Math.max(1, ...data.map(d => d[valueKey] || 0)));
  const slot = innerW / n;
  const barW = Math.max(2, slot * 0.62);
  const yAt = (v) => padT + innerH - (v / maxV) * innerH;
  const ticks = 4;
  const tickVals = range(ticks + 1).map(i => (maxV * i) / ticks);
  const [hover, setHover] = React.useState(null);

  return (
    <div ref={wrapRef} className="w-full relative">
      <svg width={w} height={height} className="block" onMouseLeave={() => setHover(null)}>
        {tickVals.map((v, idx) => (
          <g key={idx}>
            <line x1={padL} x2={w - padR} y1={yAt(v)} y2={yAt(v)} stroke="rgb(244 244 245)" />
            <text x={padL - 8} y={yAt(v) + 4} textAnchor="end" className="fill-zinc-400 text-[10px] tnum">
              {yFormatter(Math.round(v))}
            </text>
          </g>
        ))}
        {[0, Math.floor(n / 3), Math.floor((2 * n) / 3), n - 1].filter((v, i, a) => a.indexOf(v) === i).map((i) => (
          <text key={i} x={padL + slot * i + slot / 2} y={height - 8} textAnchor="middle" className="fill-zinc-400 text-[10px]">
            {formatDateShort(data[i].date)}
          </text>
        ))}
        {data.map((d, i) => {
          const h = (d[valueKey] || 0) / maxV * innerH;
          const x = padL + slot * i + (slot - barW) / 2;
          const y = padT + innerH - h;
          const isHover = hover && hover.i === i;
          return (
            <rect
              key={i}
              x={x} y={y} width={barW} height={Math.max(0, h)}
              fill={color}
              opacity={isHover ? 1 : 0.85}
              rx="2"
              onMouseEnter={() => setHover({ i, x: x + barW / 2, y })}
            />
          );
        })}
      </svg>
      {hover && (
        <div className="pointer-events-none absolute bg-white border border-zinc-200 shadow-pop rounded-md px-3 py-2 text-xs"
             style={{ left: Math.min(w - 200, Math.max(0, hover.x - 90)), top: Math.max(0, hover.y - 56) }}>
          <div className="text-zinc-500 mb-0.5">{formatDate(data[hover.i].date)}</div>
          <div className="font-medium text-zinc-900 tnum">{tooltipFormatter ? tooltipFormatter(data[hover.i]) : yFormatter(data[hover.i][valueKey])}</div>
        </div>
      )}
    </div>
  );
};

// Tiny inline sparkline for stat cards
const Sparkline = ({ data, color = 'rgb(24 24 27)', width = 100, height = 32 }) => {
  const max = Math.max(1, ...data);
  const step = width / Math.max(1, data.length - 1);
  const pts = data.map((v, i) => `${i * step},${height - (v / max) * (height - 4) - 2}`).join(' ');
  return (
    <svg width={width} height={height} className="block">
      <polyline points={pts} fill="none" stroke={color} strokeWidth="1.5" strokeLinejoin="round" strokeLinecap="round" />
    </svg>
  );
};

Object.assign(window, { LineChart, BarChart, Sparkline });
