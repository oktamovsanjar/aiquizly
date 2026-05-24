
// tweaks-panel.jsx
// Reusable Tweaks shell + form-control helpers.
//
// Owns the host protocol (listens for __activate_edit_mode / __deactivate_edit_mode,
// posts __edit_mode_available / __edit_mode_set_keys / __edit_mode_dismissed) so
// individual prototypes don't re-roll it. Ships a consistent set of controls so you
// don't hand-draw <input type="range">, segmented radios, steppers, etc.
//
// Usage (in an HTML file that loads React + Babel):
//
//   const TWEAK_DEFAULTS = /*EDITMODE-BEGIN*/{
//     "primaryColor": "#D97757",
//     "palette": ["#D97757", "#29261b", "#f6f4ef"],
//     "fontSize": 16,
//     "density": "regular",
//     "dark": false
//   }/*EDITMODE-END*/;
//
//   function App() {
//     const [t, setTweak] = useTweaks(TWEAK_DEFAULTS);
//     return (
//       <div style={{ fontSize: t.fontSize, color: t.primaryColor }}>
//         Hello
//         <TweaksPanel>
//           <TweakSection label="Typography" />
//           <TweakSlider label="Font size" value={t.fontSize} min={10} max={32} unit="px"
//                        onChange={(v) => setTweak('fontSize', v)} />
//           <TweakRadio  label="Density" value={t.density}
//                        options={['compact', 'regular', 'comfy']}
//                        onChange={(v) => setTweak('density', v)} />
//           <TweakSection label="Theme" />
//           <TweakColor  label="Primary" value={t.primaryColor}
//                        options={['#D97757', '#2A6FDB', '#1F8A5B', '#7A5AE0']}
//                        onChange={(v) => setTweak('primaryColor', v)} />
//           <TweakColor  label="Palette" value={t.palette}
//                        options={[['#D97757', '#29261b', '#f6f4ef'],
//                                  ['#475569', '#0f172a', '#f1f5f9']]}
//                        onChange={(v) => setTweak('palette', v)} />
//           <TweakToggle label="Dark mode" value={t.dark}
//                        onChange={(v) => setTweak('dark', v)} />
//         </TweaksPanel>
//       </div>
//     );
//   }
//
// ─────────────────────────────────────────────────────────────────────────────

const __TWEAKS_STYLE = `
  .twk-panel{position:fixed;right:16px;bottom:16px;z-index:2147483646;width:280px;
    max-height:calc(100vh - 32px);display:flex;flex-direction:column;
    transform:scale(var(--dc-inv-zoom,1));transform-origin:bottom right;
    background:rgba(250,249,247,.78);color:#29261b;
    -webkit-backdrop-filter:blur(24px) saturate(160%);backdrop-filter:blur(24px) saturate(160%);
    border:.5px solid rgba(255,255,255,.6);border-radius:14px;
    box-shadow:0 1px 0 rgba(255,255,255,.5) inset,0 12px 40px rgba(0,0,0,.18);
    font:11.5px/1.4 ui-sans-serif,system-ui,-apple-system,sans-serif;overflow:hidden}
  .twk-hd{display:flex;align-items:center;justify-content:space-between;
    padding:10px 8px 10px 14px;cursor:move;user-select:none}
  .twk-hd b{font-size:12px;font-weight:600;letter-spacing:.01em}
  .twk-x{appearance:none;border:0;background:transparent;color:rgba(41,38,27,.55);
    width:22px;height:22px;border-radius:6px;cursor:default;font-size:13px;line-height:1}
  .twk-x:hover{background:rgba(0,0,0,.06);color:#29261b}
  .twk-body{padding:2px 14px 14px;display:flex;flex-direction:column;gap:10px;
    overflow-y:auto;overflow-x:hidden;min-height:0;
    scrollbar-width:thin;scrollbar-color:rgba(0,0,0,.15) transparent}
  .twk-body::-webkit-scrollbar{width:8px}
  .twk-body::-webkit-scrollbar-track{background:transparent;margin:2px}
  .twk-body::-webkit-scrollbar-thumb{background:rgba(0,0,0,.15);border-radius:4px;
    border:2px solid transparent;background-clip:content-box}
  .twk-body::-webkit-scrollbar-thumb:hover{background:rgba(0,0,0,.25);
    border:2px solid transparent;background-clip:content-box}
  .twk-row{display:flex;flex-direction:column;gap:5px}
  .twk-row-h{flex-direction:row;align-items:center;justify-content:space-between;gap:10px}
  .twk-lbl{display:flex;justify-content:space-between;align-items:baseline;
    color:rgba(41,38,27,.72)}
  .twk-lbl>span:first-child{font-weight:500}
  .twk-val{color:rgba(41,38,27,.5);font-variant-numeric:tabular-nums}

  .twk-sect{font-size:10px;font-weight:600;letter-spacing:.06em;text-transform:uppercase;
    color:rgba(41,38,27,.45);padding:10px 0 0}
  .twk-sect:first-child{padding-top:0}

  .twk-field{appearance:none;box-sizing:border-box;width:100%;min-width:0;height:26px;padding:0 8px;
    border:.5px solid rgba(0,0,0,.1);border-radius:7px;
    background:rgba(255,255,255,.6);color:inherit;font:inherit;outline:none}
  .twk-field:focus{border-color:rgba(0,0,0,.25);background:rgba(255,255,255,.85)}
  select.twk-field{padding-right:22px;
    background-image:url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='10' height='6' viewBox='0 0 10 6'><path fill='rgba(0,0,0,.5)' d='M0 0h10L5 6z'/></svg>");
    background-repeat:no-repeat;background-position:right 8px center}

  .twk-slider{appearance:none;-webkit-appearance:none;width:100%;height:4px;margin:6px 0;
    border-radius:999px;background:rgba(0,0,0,.12);outline:none}
  .twk-slider::-webkit-slider-thumb{-webkit-appearance:none;appearance:none;
    width:14px;height:14px;border-radius:50%;background:#fff;
    border:.5px solid rgba(0,0,0,.12);box-shadow:0 1px 3px rgba(0,0,0,.2);cursor:default}
  .twk-slider::-moz-range-thumb{width:14px;height:14px;border-radius:50%;
    background:#fff;border:.5px solid rgba(0,0,0,.12);box-shadow:0 1px 3px rgba(0,0,0,.2);cursor:default}

  .twk-seg{position:relative;display:flex;padding:2px;border-radius:8px;
    background:rgba(0,0,0,.06);user-select:none}
  .twk-seg-thumb{position:absolute;top:2px;bottom:2px;border-radius:6px;
    background:rgba(255,255,255,.9);box-shadow:0 1px 2px rgba(0,0,0,.12);
    transition:left .15s cubic-bezier(.3,.7,.4,1),width .15s}
  .twk-seg.dragging .twk-seg-thumb{transition:none}
  .twk-seg button{appearance:none;position:relative;z-index:1;flex:1;border:0;
    background:transparent;color:inherit;font:inherit;font-weight:500;min-height:22px;
    border-radius:6px;cursor:default;padding:4px 6px;line-height:1.2;
    overflow-wrap:anywhere}

  .twk-toggle{position:relative;width:32px;height:18px;border:0;border-radius:999px;
    background:rgba(0,0,0,.15);transition:background .15s;cursor:default;padding:0}
  .twk-toggle[data-on="1"]{background:#34c759}
  .twk-toggle i{position:absolute;top:2px;left:2px;width:14px;height:14px;border-radius:50%;
    background:#fff;box-shadow:0 1px 2px rgba(0,0,0,.25);transition:transform .15s}
  .twk-toggle[data-on="1"] i{transform:translateX(14px)}

  .twk-num{display:flex;align-items:center;box-sizing:border-box;min-width:0;height:26px;padding:0 0 0 8px;
    border:.5px solid rgba(0,0,0,.1);border-radius:7px;background:rgba(255,255,255,.6)}
  .twk-num-lbl{font-weight:500;color:rgba(41,38,27,.6);cursor:ew-resize;
    user-select:none;padding-right:8px}
  .twk-num input{flex:1;min-width:0;height:100%;border:0;background:transparent;
    font:inherit;font-variant-numeric:tabular-nums;text-align:right;padding:0 8px 0 0;
    outline:none;color:inherit;-moz-appearance:textfield}
  .twk-num input::-webkit-inner-spin-button,.twk-num input::-webkit-outer-spin-button{
    -webkit-appearance:none;margin:0}
  .twk-num-unit{padding-right:8px;color:rgba(41,38,27,.45)}

  .twk-btn{appearance:none;height:26px;padding:0 12px;border:0;border-radius:7px;
    background:rgba(0,0,0,.78);color:#fff;font:inherit;font-weight:500;cursor:default}
  .twk-btn:hover{background:rgba(0,0,0,.88)}
  .twk-btn.secondary{background:rgba(0,0,0,.06);color:inherit}
  .twk-btn.secondary:hover{background:rgba(0,0,0,.1)}

  .twk-swatch{appearance:none;-webkit-appearance:none;width:56px;height:22px;
    border:.5px solid rgba(0,0,0,.1);border-radius:6px;padding:0;cursor:default;
    background:transparent;flex-shrink:0}
  .twk-swatch::-webkit-color-swatch-wrapper{padding:0}
  .twk-swatch::-webkit-color-swatch{border:0;border-radius:5.5px}
  .twk-swatch::-moz-color-swatch{border:0;border-radius:5.5px}

  .twk-chips{display:flex;gap:6px}
  .twk-chip{position:relative;appearance:none;flex:1;min-width:0;height:46px;
    padding:0;border:0;border-radius:6px;overflow:hidden;cursor:default;
    box-shadow:0 0 0 .5px rgba(0,0,0,.12),0 1px 2px rgba(0,0,0,.06);
    transition:transform .12s cubic-bezier(.3,.7,.4,1),box-shadow .12s}
  .twk-chip:hover{transform:translateY(-1px);
    box-shadow:0 0 0 .5px rgba(0,0,0,.18),0 4px 10px rgba(0,0,0,.12)}
  .twk-chip[data-on="1"]{box-shadow:0 0 0 1.5px rgba(0,0,0,.85),
    0 2px 6px rgba(0,0,0,.15)}
  .twk-chip>span{position:absolute;top:0;bottom:0;right:0;width:34%;
    display:flex;flex-direction:column;box-shadow:-1px 0 0 rgba(0,0,0,.1)}
  .twk-chip>span>i{flex:1;box-shadow:0 -1px 0 rgba(0,0,0,.1)}
  .twk-chip>span>i:first-child{box-shadow:none}
  .twk-chip svg{position:absolute;top:6px;left:6px;width:13px;height:13px;
    filter:drop-shadow(0 1px 1px rgba(0,0,0,.3))}
`;

// ── useTweaks ───────────────────────────────────────────────────────────────
// Single source of truth for tweak values. setTweak persists via the host
// (__edit_mode_set_keys → host rewrites the EDITMODE block on disk).
function useTweaks(defaults) {
  const [values, setValues] = React.useState(defaults);
  // Accepts either setTweak('key', value) or setTweak({ key: value, ... }) so a
  // useState-style call doesn't write a "[object Object]" key into the persisted
  // JSON block.
  const setTweak = React.useCallback((keyOrEdits, val) => {
    const edits = typeof keyOrEdits === 'object' && keyOrEdits !== null
      ? keyOrEdits : { [keyOrEdits]: val };
    setValues((prev) => ({ ...prev, ...edits }));
    window.parent.postMessage({ type: '__edit_mode_set_keys', edits }, '*');
    // Same-window signal so in-page listeners (deck-stage rail thumbnails)
    // can react — the parent message only reaches the host, not peers.
    window.dispatchEvent(new CustomEvent('tweakchange', { detail: edits }));
  }, []);
  return [values, setTweak];
}

// ── TweaksPanel ─────────────────────────────────────────────────────────────
// Floating shell. Registers the protocol listener BEFORE announcing
// availability — if the announce ran first, the host's activate could land
// before our handler exists and the toolbar toggle would silently no-op.
// The close button posts __edit_mode_dismissed so the host's toolbar toggle
// flips off in lockstep; the host echoes __deactivate_edit_mode back which
// is what actually hides the panel.
function TweaksPanel({ title = 'Tweaks', noDeckControls = false, children }) {
  const [open, setOpen] = React.useState(false);
  const dragRef = React.useRef(null);
  // Auto-inject a rail toggle when a <deck-stage> is on the page. The
  // toggle drives the deck's per-viewer _railVisible via window message;
  // state is mirrored from the same localStorage key the deck reads so
  // the control reflects reality across reloads. The mechanism is the
  // message — authors who want custom placement can post it directly
  // and pass noDeckControls to suppress this one.
  const hasDeckStage = React.useMemo(
    () => typeof document !== 'undefined' && !!document.querySelector('deck-stage'),
    [],
  );
  // deck-stage enables its rail in connectedCallback, but this panel can
  // mount before that element has upgraded. The initial read catches the
  // common case; the listener covers mounting first. (Older deck-stage.js
  // copies still wait for the host's __omelette_rail_enabled postMessage —
  // same listener handles those.)
  const [railEnabled, setRailEnabled] = React.useState(
    () => hasDeckStage && !!document.querySelector('deck-stage')?._railEnabled,
  );
  React.useEffect(() => {
    if (!hasDeckStage || railEnabled) return undefined;
    const onMsg = (e) => {
      if (e.data && e.data.type === '__omelette_rail_enabled') setRailEnabled(true);
    };
    window.addEventListener('message', onMsg);
    return () => window.removeEventListener('message', onMsg);
  }, [hasDeckStage, railEnabled]);
  const [railVisible, setRailVisible] = React.useState(() => {
    try { return localStorage.getItem('deck-stage.railVisible') !== '0'; } catch (e) { return true; }
  });
  const toggleRail = (on) => {
    setRailVisible(on);
    window.postMessage({ type: '__deck_rail_visible', on }, '*');
  };
  const offsetRef = React.useRef({ x: 16, y: 16 });
  const PAD = 16;

  const clampToViewport = React.useCallback(() => {
    const panel = dragRef.current;
    if (!panel) return;
    const w = panel.offsetWidth, h = panel.offsetHeight;
    const maxRight = Math.max(PAD, window.innerWidth - w - PAD);
    const maxBottom = Math.max(PAD, window.innerHeight - h - PAD);
    offsetRef.current = {
      x: Math.min(maxRight, Math.max(PAD, offsetRef.current.x)),
      y: Math.min(maxBottom, Math.max(PAD, offsetRef.current.y)),
    };
    panel.style.right = offsetRef.current.x + 'px';
    panel.style.bottom = offsetRef.current.y + 'px';
  }, []);

  React.useEffect(() => {
    if (!open) return;
    clampToViewport();
    if (typeof ResizeObserver === 'undefined') {
      window.addEventListener('resize', clampToViewport);
      return () => window.removeEventListener('resize', clampToViewport);
    }
    const ro = new ResizeObserver(clampToViewport);
    ro.observe(document.documentElement);
    return () => ro.disconnect();
  }, [open, clampToViewport]);

  React.useEffect(() => {
    const onMsg = (e) => {
      const t = e?.data?.type;
      if (t === '__activate_edit_mode') setOpen(true);
      else if (t === '__deactivate_edit_mode') setOpen(false);
    };
    window.addEventListener('message', onMsg);
    window.parent.postMessage({ type: '__edit_mode_available' }, '*');
    return () => window.removeEventListener('message', onMsg);
  }, []);

  const dismiss = () => {
    setOpen(false);
    window.parent.postMessage({ type: '__edit_mode_dismissed' }, '*');
  };

  const onDragStart = (e) => {
    const panel = dragRef.current;
    if (!panel) return;
    const r = panel.getBoundingClientRect();
    const sx = e.clientX, sy = e.clientY;
    const startRight = window.innerWidth - r.right;
    const startBottom = window.innerHeight - r.bottom;
    const move = (ev) => {
      offsetRef.current = {
        x: startRight - (ev.clientX - sx),
        y: startBottom - (ev.clientY - sy),
      };
      clampToViewport();
    };
    const up = () => {
      window.removeEventListener('mousemove', move);
      window.removeEventListener('mouseup', up);
    };
    window.addEventListener('mousemove', move);
    window.addEventListener('mouseup', up);
  };

  if (!open) return null;
  return (
    <>
      <style>{__TWEAKS_STYLE}</style>
      <div ref={dragRef} className="twk-panel" data-noncommentable=""
           style={{ right: offsetRef.current.x, bottom: offsetRef.current.y }}>
        <div className="twk-hd" onMouseDown={onDragStart}>
          <b>{title}</b>
          <button className="twk-x" aria-label="Close tweaks"
                  onMouseDown={(e) => e.stopPropagation()}
                  onClick={dismiss}>✕</button>
        </div>
        <div className="twk-body">
          {children}
          {hasDeckStage && railEnabled && !noDeckControls && (
            <TweakSection label="Deck">
              <TweakToggle label="Thumbnail rail" value={railVisible} onChange={toggleRail} />
            </TweakSection>
          )}
        </div>
      </div>
    </>
  );
}

// ── Layout helpers ──────────────────────────────────────────────────────────

function TweakSection({ label, children }) {
  return (
    <>
      <div className="twk-sect">{label}</div>
      {children}
    </>
  );
}

function TweakRow({ label, value, children, inline = false }) {
  return (
    <div className={inline ? 'twk-row twk-row-h' : 'twk-row'}>
      <div className="twk-lbl">
        <span>{label}</span>
        {value != null && <span className="twk-val">{value}</span>}
      </div>
      {children}
    </div>
  );
}

// ── Controls ────────────────────────────────────────────────────────────────

function TweakSlider({ label, value, min = 0, max = 100, step = 1, unit = '', onChange }) {
  return (
    <TweakRow label={label} value={`${value}${unit}`}>
      <input type="range" className="twk-slider" min={min} max={max} step={step}
             value={value} onChange={(e) => onChange(Number(e.target.value))} />
    </TweakRow>
  );
}

function TweakToggle({ label, value, onChange }) {
  return (
    <div className="twk-row twk-row-h">
      <div className="twk-lbl"><span>{label}</span></div>
      <button type="button" className="twk-toggle" data-on={value ? '1' : '0'}
              role="switch" aria-checked={!!value}
              onClick={() => onChange(!value)}><i /></button>
    </div>
  );
}

function TweakRadio({ label, value, options, onChange }) {
  const trackRef = React.useRef(null);
  const [dragging, setDragging] = React.useState(false);
  // The active value is read by pointer-move handlers attached for the lifetime
  // of a drag — ref it so a stale closure doesn't fire onChange for every move.
  const valueRef = React.useRef(value);
  valueRef.current = value;

  // Segments wrap mid-word once per-segment width runs out. The track is
  // ~248px (280 panel − 28 body pad − 4 seg pad), each button loses 12px
  // to its own padding, and 11.5px system-ui averages ~6.3px/char — so 2
  // options fit ~16 chars each, 3 fit ~10. Past that (or >3 options), fall
  // back to a dropdown rather than wrap.
  const labelLen = (o) => String(typeof o === 'object' ? o.label : o).length;
  const maxLen = options.reduce((m, o) => Math.max(m, labelLen(o)), 0);
  const fitsAsSegments = maxLen <= ({ 2: 16, 3: 10 }[options.length] ?? 0);
  if (!fitsAsSegments) {
    // <select> emits strings — map back to the original option value so the
    // fallback stays type-preserving (numbers, booleans) like the segment path.
    const resolve = (s) => {
      const m = options.find((o) => String(typeof o === 'object' ? o.value : o) === s);
      return m === undefined ? s : typeof m === 'object' ? m.value : m;
    };
    return <TweakSelect label={label} value={value} options={options}
                        onChange={(s) => onChange(resolve(s))} />;
  }
  const opts = options.map((o) => (typeof o === 'object' ? o : { value: o, label: o }));
  const idx = Math.max(0, opts.findIndex((o) => o.value === value));
  const n = opts.length;

  const segAt = (clientX) => {
    const r = trackRef.current.getBoundingClientRect();
    const inner = r.width - 4;
    const i = Math.floor(((clientX - r.left - 2) / inner) * n);
    return opts[Math.max(0, Math.min(n - 1, i))].value;
  };

  const onPointerDown = (e) => {
    setDragging(true);
    const v0 = segAt(e.clientX);
    if (v0 !== valueRef.current) onChange(v0);
    const move = (ev) => {
      if (!trackRef.current) return;
      const v = segAt(ev.clientX);
      if (v !== valueRef.current) onChange(v);
    };
    const up = () => {
      setDragging(false);
      window.removeEventListener('pointermove', move);
      window.removeEventListener('pointerup', up);
    };
    window.addEventListener('pointermove', move);
    window.addEventListener('pointerup', up);
  };

  return (
    <TweakRow label={label}>
      <div ref={trackRef} role="radiogroup" onPointerDown={onPointerDown}
           className={dragging ? 'twk-seg dragging' : 'twk-seg'}>
        <div className="twk-seg-thumb"
             style={{ left: `calc(2px + ${idx} * (100% - 4px) / ${n})`,
                      width: `calc((100% - 4px) / ${n})` }} />
        {opts.map((o) => (
          <button key={o.value} type="button" role="radio" aria-checked={o.value === value}>
            {o.label}
          </button>
        ))}
      </div>
    </TweakRow>
  );
}

function TweakSelect({ label, value, options, onChange }) {
  return (
    <TweakRow label={label}>
      <select className="twk-field" value={value} onChange={(e) => onChange(e.target.value)}>
        {options.map((o) => {
          const v = typeof o === 'object' ? o.value : o;
          const l = typeof o === 'object' ? o.label : o;
          return <option key={v} value={v}>{l}</option>;
        })}
      </select>
    </TweakRow>
  );
}

function TweakText({ label, value, placeholder, onChange }) {
  return (
    <TweakRow label={label}>
      <input className="twk-field" type="text" value={value} placeholder={placeholder}
             onChange={(e) => onChange(e.target.value)} />
    </TweakRow>
  );
}

function TweakNumber({ label, value, min, max, step = 1, unit = '', onChange }) {
  const clamp = (n) => {
    if (min != null && n < min) return min;
    if (max != null && n > max) return max;
    return n;
  };
  const startRef = React.useRef({ x: 0, val: 0 });
  const onScrubStart = (e) => {
    e.preventDefault();
    startRef.current = { x: e.clientX, val: value };
    const decimals = (String(step).split('.')[1] || '').length;
    const move = (ev) => {
      const dx = ev.clientX - startRef.current.x;
      const raw = startRef.current.val + dx * step;
      const snapped = Math.round(raw / step) * step;
      onChange(clamp(Number(snapped.toFixed(decimals))));
    };
    const up = () => {
      window.removeEventListener('pointermove', move);
      window.removeEventListener('pointerup', up);
    };
    window.addEventListener('pointermove', move);
    window.addEventListener('pointerup', up);
  };
  return (
    <div className="twk-num">
      <span className="twk-num-lbl" onPointerDown={onScrubStart}>{label}</span>
      <input type="number" value={value} min={min} max={max} step={step}
             onChange={(e) => onChange(clamp(Number(e.target.value)))} />
      {unit && <span className="twk-num-unit">{unit}</span>}
    </div>
  );
}

// Relative-luminance contrast pick — checkmarks drawn over a swatch need to
// read on both #111 and #fafafa without per-option configuration. Hex input
// only (#rgb / #rrggbb); named or rgb()/hsl() colors fall through to "light".
function __twkIsLight(hex) {
  const h = String(hex).replace('#', '');
  const x = h.length === 3 ? h.replace(/./g, (c) => c + c) : h.padEnd(6, '0');
  const n = parseInt(x.slice(0, 6), 16);
  if (Number.isNaN(n)) return true;
  const r = (n >> 16) & 255, g = (n >> 8) & 255, b = n & 255;
  return r * 299 + g * 587 + b * 114 > 148000;
}

const __TwkCheck = ({ light }) => (
  <svg viewBox="0 0 14 14" aria-hidden="true">
    <path d="M3 7.2 5.8 10 11 4.2" fill="none" strokeWidth="2.2"
          strokeLinecap="round" strokeLinejoin="round"
          stroke={light ? 'rgba(0,0,0,.78)' : '#fff'} />
  </svg>
);

// TweakColor — curated color/palette picker. Each option is either a single
// hex string or an array of 1-5 hex strings; the card adapts — a lone color
// renders solid, a palette renders colors[0] as the hero (left ~2/3) with the
// rest stacked in a sharp column on the right. onChange emits the
// option in the shape it was passed (string stays string, array stays array).
// Without options it falls back to the native color input for back-compat.
function TweakColor({ label, value, options, onChange }) {
  if (!options || !options.length) {
    return (
      <div className="twk-row twk-row-h">
        <div className="twk-lbl"><span>{label}</span></div>
        <input type="color" className="twk-swatch" value={value}
               onChange={(e) => onChange(e.target.value)} />
      </div>
    );
  }
  // Native <input type=color> emits lowercase hex per the HTML spec, so
  // compare case-insensitively. String() guards JSON.stringify(undefined),
  // which returns the primitive undefined (no .toLowerCase).
  const key = (o) => String(JSON.stringify(o)).toLowerCase();
  const cur = key(value);
  return (
    <TweakRow label={label}>
      <div className="twk-chips" role="radiogroup">
        {options.map((o, i) => {
          const colors = Array.isArray(o) ? o : [o];
          const [hero, ...rest] = colors;
          const sup = rest.slice(0, 4);
          const on = key(o) === cur;
          return (
            <button key={i} type="button" className="twk-chip" role="radio"
                    aria-checked={on} data-on={on ? '1' : '0'}
                    aria-label={colors.join(', ')} title={colors.join(' · ')}
                    style={{ background: hero }}
                    onClick={() => onChange(o)}>
              {sup.length > 0 && (
                <span>
                  {sup.map((c, j) => <i key={j} style={{ background: c }} />)}
                </span>
              )}
              {on && <__TwkCheck light={__twkIsLight(hero)} />}
            </button>
          );
        })}
      </div>
    </TweakRow>
  );
}

function TweakButton({ label, onClick, secondary = false }) {
  return (
    <button type="button" className={secondary ? 'twk-btn secondary' : 'twk-btn'}
            onClick={onClick}>{label}</button>
  );
}

Object.assign(window, {
  useTweaks, TweaksPanel, TweakSection, TweakRow,
  TweakSlider, TweakToggle, TweakRadio, TweakSelect,
  TweakText, TweakNumber, TweakColor, TweakButton,
});
// Inline lucide-style SVG icons. Stroke 2, 24x24, currentColor.
// Sized via className (default w-4 h-4).
const Icon = ({ children, className = 'w-4 h-4', strokeWidth = 2, ...props }) => (
  <svg
    xmlns="http://www.w3.org/2000/svg"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth={strokeWidth}
    strokeLinecap="round"
    strokeLinejoin="round"
    className={className}
    {...props}
  >
    {children}
  </svg>
);

const IconLayoutDashboard = (p) => (
  <Icon {...p}>
    <rect x="3" y="3" width="7" height="9" rx="1" />
    <rect x="14" y="3" width="7" height="5" rx="1" />
    <rect x="14" y="12" width="7" height="9" rx="1" />
    <rect x="3" y="16" width="7" height="5" rx="1" />
  </Icon>
);
const IconUsers = (p) => (
  <Icon {...p}>
    <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" />
    <circle cx="9" cy="7" r="4" />
    <path d="M22 21v-2a4 4 0 0 0-3-3.87" />
    <path d="M16 3.13a4 4 0 0 1 0 7.75" />
  </Icon>
);
const IconBookOpen = (p) => (
  <Icon {...p}>
    <path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z" />
    <path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z" />
  </Icon>
);
const IconFileImport = (p) => (
  <Icon {...p}>
    <path d="M14 3v4a1 1 0 0 0 1 1h4" />
    <path d="M17 21H7a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h7l5 5v11a2 2 0 0 1-2 2z" />
    <path d="M9 14l3 3 3-3" />
    <path d="M12 11v6" />
  </Icon>
);
const IconBell = (p) => (
  <Icon {...p}>
    <path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9" />
    <path d="M10.3 21a1.94 1.94 0 0 0 3.4 0" />
  </Icon>
);
const IconMessageSquare = (p) => (
  <Icon {...p}>
    <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
  </Icon>
);
const IconSettings = (p) => (
  <Icon {...p}>
    <path d="M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6z" />
    <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" />
  </Icon>
);
const IconSearch = (p) => (
  <Icon {...p}>
    <circle cx="11" cy="11" r="8" />
    <path d="m21 21-4.3-4.3" />
  </Icon>
);
const IconChevronDown = (p) => (<Icon {...p}><path d="m6 9 6 6 6-6" /></Icon>);
const IconChevronRight = (p) => (<Icon {...p}><path d="m9 18 6-6-6-6" /></Icon>);
const IconChevronLeft = (p) => (<Icon {...p}><path d="m15 18-6-6 6-6" /></Icon>);
const IconChevronUp = (p) => (<Icon {...p}><path d="m18 15-6-6-6 6" /></Icon>);
const IconPlus = (p) => (<Icon {...p}><path d="M5 12h14M12 5v14" /></Icon>);
const IconX = (p) => (<Icon {...p}><path d="M18 6 6 18M6 6l12 12" /></Icon>);
const IconCheck = (p) => (<Icon {...p}><path d="M20 6 9 17l-5-5" /></Icon>);
const IconMoreH = (p) => (<Icon {...p}><circle cx="12" cy="12" r="1"/><circle cx="19" cy="12" r="1"/><circle cx="5" cy="12" r="1"/></Icon>);
const IconTrash = (p) => (
  <Icon {...p}>
    <path d="M3 6h18" />
    <path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
    <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6" />
    <path d="M10 11v6M14 11v6" />
  </Icon>
);
const IconRotate = (p) => (
  <Icon {...p}>
    <path d="M3 12a9 9 0 1 0 3-6.7L3 8" />
    <path d="M3 3v5h5" />
  </Icon>
);
const IconEye = (p) => (<Icon {...p}><path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12z"/><circle cx="12" cy="12" r="3"/></Icon>);
const IconEyeOff = (p) => (<Icon {...p}><path d="M17.94 17.94A10.94 10.94 0 0 1 12 19c-7 0-10-7-10-7a19.6 19.6 0 0 1 4.06-5.94"/><path d="M9.9 4.24A10.9 10.9 0 0 1 12 4c7 0 10 7 10 7a19.7 19.7 0 0 1-2.16 3.19"/><path d="M14.12 14.12a3 3 0 0 1-4.24-4.24"/><path d="m2 2 20 20"/></Icon>);
const IconLock = (p) => (<Icon {...p}><rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></Icon>);
const IconShield = (p) => (<Icon {...p}><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></Icon>);
const IconTrendUp = (p) => (<Icon {...p}><polyline points="22 7 13.5 15.5 8.5 10.5 2 17"/><polyline points="16 7 22 7 22 13"/></Icon>);
const IconTrendDown = (p) => (<Icon {...p}><polyline points="22 17 13.5 8.5 8.5 13.5 2 7"/><polyline points="16 17 22 17 22 11"/></Icon>);
const IconWallet = (p) => (<Icon {...p}><path d="M21 12V7a2 2 0 0 0-2-2H5a2 2 0 0 0 0 4h16v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V7"/><path d="M16 14h.01"/></Icon>);
const IconActivity = (p) => (<Icon {...p}><path d="M22 12h-4l-3 9L9 3l-3 9H2"/></Icon>);
const IconBan = (p) => (<Icon {...p}><circle cx="12" cy="12" r="10"/><path d="m4.9 4.9 14.2 14.2"/></Icon>);
const IconSend = (p) => (<Icon {...p}><path d="m22 2-7 20-4-9-9-4z"/><path d="M22 2 11 13"/></Icon>);
const IconGlobe = (p) => (<Icon {...p}><circle cx="12" cy="12" r="10"/><path d="M2 12h20"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/></Icon>);
const IconCommand = (p) => (<Icon {...p}><path d="M18 3a3 3 0 0 0-3 3v12a3 3 0 0 0 3 3 3 3 0 0 0 3-3 3 3 0 0 0-3-3H6a3 3 0 0 0-3 3 3 3 0 0 0 3 3 3 3 0 0 0 3-3V6a3 3 0 0 0-3-3 3 3 0 0 0-3 3 3 3 0 0 0 3 3h12a3 3 0 0 0 3-3 3 3 0 0 0-3-3z"/></Icon>);
const IconLogout = (p) => (<Icon {...p}><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><path d="M16 17l5-5-5-5"/><path d="M21 12H9"/></Icon>);
const IconCircle = (p) => (<Icon {...p}><circle cx="12" cy="12" r="10"/></Icon>);
const IconDot = (p) => (<Icon {...p}><circle cx="12" cy="12" r="4" fill="currentColor"/></Icon>);
const IconLoader = (p) => (<Icon {...p}><path d="M21 12a9 9 0 1 1-6.219-8.56"/></Icon>);
const IconFile = (p) => (<Icon {...p}><path d="M14 3v4a1 1 0 0 0 1 1h4"/><path d="M17 21H7a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h7l5 5v11a2 2 0 0 1-2 2z"/></Icon>);
const IconClock = (p) => (<Icon {...p}><circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/></Icon>);
const IconBolt = (p) => (<Icon {...p}><path d="M13 2 3 14h9l-1 8 10-12h-9l1-8z"/></Icon>);
const IconCalendar = (p) => (<Icon {...p}><rect x="3" y="4" width="18" height="18" rx="2"/><path d="M16 2v4M8 2v4M3 10h18"/></Icon>);
const IconKey = (p) => (<Icon {...p}><circle cx="7.5" cy="15.5" r="5.5"/><path d="m21 2-9.6 9.6"/><path d="m15.5 7.5 3 3L22 7l-3-3"/></Icon>);
const IconCopy = (p) => (<Icon {...p}><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></Icon>);
const IconFilter = (p) => (<Icon {...p}><polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3"/></Icon>);
const IconArrowUpRight = (p) => (<Icon {...p}><path d="M7 17 17 7"/><path d="M7 7h10v10"/></Icon>);

Object.assign(window, {
  Icon,
  IconLayoutDashboard, IconUsers, IconBookOpen, IconFileImport, IconBell,
  IconMessageSquare, IconSettings, IconSearch, IconChevronDown, IconChevronRight,
  IconChevronLeft, IconChevronUp, IconPlus, IconX, IconCheck, IconMoreH,
  IconTrash, IconRotate, IconEye, IconEyeOff, IconLock, IconShield,
  IconTrendUp, IconTrendDown, IconWallet, IconActivity, IconBan, IconSend,
  IconGlobe, IconCommand, IconLogout, IconCircle, IconDot, IconLoader,
  IconFile, IconClock, IconBolt, IconCalendar, IconKey, IconCopy, IconFilter,
  IconArrowUpRight,
});
// shadcn-style primitives: Button, Card, Badge, Input, Textarea, Select,
// Table, Tabs, Dialog, Skeleton, Switch, Toaster.

const cx = (...a) => a.filter(Boolean).join(' ');

// ---- Button ----------------------------------------------------------------
const Button = React.forwardRef(({
  variant = 'default', size = 'md', className = '', children, ...props
}, ref) => {
  const base = 'inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md text-sm font-medium transition disabled:pointer-events-none disabled:opacity-50 ring-base';
  const variants = {
    default: 'bg-zinc-900 text-zinc-50 hover:bg-zinc-900/90 shadow-sm',
    secondary: 'bg-zinc-100 text-zinc-900 hover:bg-zinc-200',
    outline: 'border border-zinc-200 bg-white text-zinc-900 hover:bg-zinc-50 shadow-sm',
    ghost: 'text-zinc-900 hover:bg-zinc-100',
    destructive: 'bg-red-600 text-white hover:bg-red-700 shadow-sm',
    link: 'text-zinc-900 underline-offset-4 hover:underline',
  };
  const sizes = {
    sm: 'h-8 px-3 text-xs',
    md: 'h-9 px-4',
    lg: 'h-10 px-6',
    icon: 'h-9 w-9 p-0',
    'icon-sm': 'h-8 w-8 p-0',
  };
  return (
    <button ref={ref} className={cx(base, variants[variant], sizes[size], className)} {...props}>
      {children}
    </button>
  );
});

// ---- Card ------------------------------------------------------------------
const Card = ({ className = '', children, ...props }) => (
  <div className={cx('rounded-xl border border-zinc-200 bg-white shadow-card', className)} {...props}>{children}</div>
);
const CardHeader = ({ className = '', children }) => (
  <div className={cx('flex flex-col gap-1.5 px-6 pt-6 pb-3', className)}>{children}</div>
);
const CardTitle = ({ className = '', children }) => (
  <h3 className={cx('text-sm font-semibold tracking-tight text-zinc-900', className)}>{children}</h3>
);
const CardDescription = ({ className = '', children }) => (
  <p className={cx('text-sm text-zinc-500', className)}>{children}</p>
);
const CardContent = ({ className = '', children }) => (
  <div className={cx('px-6 pb-6', className)}>{children}</div>
);
const CardFooter = ({ className = '', children }) => (
  <div className={cx('flex items-center px-6 py-4 border-t border-zinc-100', className)}>{children}</div>
);

// ---- Badge -----------------------------------------------------------------
const Badge = ({ tone = 'neutral', className = '', children, dot = false }) => {
  const tones = {
    neutral: 'bg-zinc-100 text-zinc-700 border-zinc-200',
    green: 'bg-emerald-50 text-emerald-700 border-emerald-200',
    red: 'bg-red-50 text-red-700 border-red-200',
    yellow: 'bg-amber-50 text-amber-800 border-amber-200',
    blue: 'bg-blue-50 text-blue-700 border-blue-200',
    violet: 'bg-violet-50 text-violet-700 border-violet-200',
    dark: 'bg-zinc-900 text-zinc-50 border-zinc-900',
  };
  const dotColor = {
    neutral: 'bg-zinc-400', green: 'bg-emerald-500', red: 'bg-red-500',
    yellow: 'bg-amber-500', blue: 'bg-blue-500', violet: 'bg-violet-500', dark: 'bg-zinc-50',
  };
  return (
    <span className={cx('inline-flex items-center gap-1.5 rounded-full border px-2 py-0.5 text-xs font-medium', tones[tone], className)}>
      {dot && <span className={cx('w-1.5 h-1.5 rounded-full', dotColor[tone])} />}
      {children}
    </span>
  );
};

// ---- Input / Textarea / Label ---------------------------------------------
const Input = React.forwardRef(({ className = '', leftIcon, ...props }, ref) => (
  <div className="relative">
    {leftIcon && <span className="absolute left-2.5 top-1/2 -translate-y-1/2 text-zinc-400">{leftIcon}</span>}
    <input
      ref={ref}
      className={cx(
        'flex h-9 w-full rounded-md border border-zinc-200 bg-white text-sm shadow-sm',
        'placeholder:text-zinc-400 transition',
        'focus:outline-none focus:ring-2 focus:ring-zinc-900/15 focus:border-zinc-300',
        'disabled:opacity-50 disabled:cursor-not-allowed',
        leftIcon ? 'pl-8 pr-3' : 'px-3',
        className
      )}
      {...props}
    />
  </div>
));

const Textarea = React.forwardRef(({ className = '', ...props }, ref) => (
  <textarea
    ref={ref}
    className={cx(
      'flex min-h-[80px] w-full rounded-md border border-zinc-200 bg-white px-3 py-2 text-sm shadow-sm',
      'placeholder:text-zinc-400 transition resize-y',
      'focus:outline-none focus:ring-2 focus:ring-zinc-900/15 focus:border-zinc-300',
      className
    )}
    {...props}
  />
));

const Label = ({ className = '', children, htmlFor }) => (
  <label htmlFor={htmlFor} className={cx('text-sm font-medium text-zinc-900', className)}>{children}</label>
);

const Select = ({ value, onChange, options, className = '', placeholder }) => (
  <div className="relative">
    <select
      value={value}
      onChange={e => onChange(e.target.value)}
      className={cx(
        'flex h-9 w-full appearance-none rounded-md border border-zinc-200 bg-white pl-3 pr-8 text-sm shadow-sm',
        'focus:outline-none focus:ring-2 focus:ring-zinc-900/15 focus:border-zinc-300',
        className
      )}
    >
      {placeholder && <option value="" disabled>{placeholder}</option>}
      {options.map(o => (
        typeof o === 'string'
          ? <option key={o} value={o}>{o}</option>
          : <option key={o.value} value={o.value}>{o.label}</option>
      ))}
    </select>
    <span className="pointer-events-none absolute right-2 top-1/2 -translate-y-1/2 text-zinc-500">
      <IconChevronDown />
    </span>
  </div>
);

// ---- Switch ----------------------------------------------------------------
const Switch = ({ checked, onChange, disabled, className = '' }) => (
  <button
    type="button"
    role="switch"
    aria-checked={checked}
    disabled={disabled}
    onClick={() => onChange(!checked)}
    className={cx(
      'relative inline-flex h-5 w-9 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition',
      'ring-base disabled:opacity-50',
      checked ? 'bg-zinc-900' : 'bg-zinc-200',
      className,
    )}
  >
    <span className={cx(
      'inline-block h-4 w-4 transform rounded-full bg-white shadow transition',
      checked ? 'translate-x-4' : 'translate-x-0'
    )} />
  </button>
);

// ---- Table -----------------------------------------------------------------
const Table = ({ children, className = '' }) => (
  <div className={cx('w-full overflow-x-auto', className)}>
    <table className="w-full caption-bottom text-sm">{children}</table>
  </div>
);
const THead = ({ children }) => (
  <thead className="border-b border-zinc-200 bg-zinc-50/50 [&_th]:h-10 [&_th]:px-4 [&_th]:text-left [&_th]:align-middle [&_th]:font-medium [&_th]:text-zinc-500 [&_th]:text-xs [&_th]:uppercase [&_th]:tracking-wide">{children}</thead>
);
const TBody = ({ children }) => (
  <tbody className="[&_tr:last-child]:border-0 [&_td]:px-4 [&_td]:align-middle">{children}</tbody>
);
const TR = ({ children, className = '', ...rest }) => (
  <tr className={cx('border-b border-zinc-100 transition hover:bg-zinc-50/70', className)} {...rest}>{children}</tr>
);

// ---- Tabs ------------------------------------------------------------------
const Tabs = ({ value, onChange, items, className = '' }) => (
  <div className={cx('inline-flex h-9 items-center justify-center rounded-lg bg-zinc-100 p-1 text-zinc-500', className)}>
    {items.map(it => (
      <button
        key={it.value}
        onClick={() => onChange(it.value)}
        className={cx(
          'inline-flex items-center justify-center whitespace-nowrap rounded-md px-3 py-1 text-sm font-medium transition',
          value === it.value ? 'bg-white text-zinc-900 shadow-sm' : 'hover:text-zinc-700',
        )}
      >
        {it.label}
        {it.count != null && (
          <span className={cx('ml-1.5 rounded px-1.5 py-0 text-xs',
            value === it.value ? 'bg-zinc-100 text-zinc-700' : 'bg-zinc-200/70 text-zinc-600')}>
            {it.count}
          </span>
        )}
      </button>
    ))}
  </div>
);

// ---- Dialog ----------------------------------------------------------------
const Dialog = ({ open, onClose, children, maxW = 'max-w-lg' }) => {
  React.useEffect(() => {
    if (!open) return;
    const onKey = (e) => { if (e.key === 'Escape') onClose(); };
    document.addEventListener('keydown', onKey);
    const prev = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      document.removeEventListener('keydown', onKey);
      document.body.style.overflow = prev;
    };
  }, [open, onClose]);
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center anim-fade">
      <div className="absolute inset-0 bg-zinc-950/50" onClick={onClose} />
      <div className={cx('relative w-full mx-4 rounded-xl border border-zinc-200 bg-white shadow-pop anim-pop', maxW)}>
        {children}
      </div>
    </div>
  );
};
const DialogHeader = ({ title, description, onClose }) => (
  <div className="flex items-start justify-between px-6 pt-6 pb-4 border-b border-zinc-100">
    <div>
      <h2 className="text-base font-semibold text-zinc-900">{title}</h2>
      {description && <p className="text-sm text-zinc-500 mt-1">{description}</p>}
    </div>
    {onClose && (
      <button onClick={onClose} className="rounded-md p-1.5 text-zinc-500 hover:bg-zinc-100">
        <IconX className="w-4 h-4" />
      </button>
    )}
  </div>
);
const DialogBody = ({ children, className = '' }) => (
  <div className={cx('px-6 py-5', className)}>{children}</div>
);
const DialogFooter = ({ children }) => (
  <div className="flex items-center justify-end gap-2 px-6 py-4 border-t border-zinc-100 bg-zinc-50/50 rounded-b-xl">{children}</div>
);

// ---- Skeleton --------------------------------------------------------------
const Skeleton = ({ className = '' }) => (
  <div className={cx('animate-pulse rounded-md bg-zinc-200/70', className)} />
);

// ---- Toaster ---------------------------------------------------------------
const ToastCtx = React.createContext(null);
const ToastProvider = ({ children }) => {
  const [toasts, setToasts] = React.useState([]);
  const push = React.useCallback((t) => {
    const id = Math.random().toString(36).slice(2);
    setToasts(ts => [...ts, { id, ...t }]);
    setTimeout(() => setToasts(ts => ts.filter(x => x.id !== id)), t.duration || 3200);
  }, []);
  const api = React.useMemo(() => ({
    success: (msg, opts) => push({ kind: 'success', msg, ...opts }),
    error:   (msg, opts) => push({ kind: 'error', msg, ...opts }),
    info:    (msg, opts) => push({ kind: 'info', msg, ...opts }),
  }), [push]);
  return (
    <ToastCtx.Provider value={api}>
      {children}
      <div className="fixed bottom-4 right-4 z-[60] flex flex-col gap-2 w-[360px] max-w-[90vw]">
        {toasts.map(t => (
          <div key={t.id} className="anim-slide rounded-lg border border-zinc-200 bg-white shadow-pop px-4 py-3 flex items-start gap-3">
            <span className={cx('mt-0.5 w-2 h-2 rounded-full shrink-0',
              t.kind === 'success' && 'bg-emerald-500',
              t.kind === 'error' && 'bg-red-500',
              t.kind === 'info' && 'bg-blue-500',
            )} />
            <div className="text-sm text-zinc-900 flex-1">{t.msg}</div>
          </div>
        ))}
      </div>
    </ToastCtx.Provider>
  );
};
const useToast = () => React.useContext(ToastCtx);

// ---- PageHeader ------------------------------------------------------------
const PageHeader = ({ title, description, children }) => (
  <div className="flex items-start justify-between gap-4 mb-6">
    <div>
      <h1 className="text-2xl font-semibold tracking-tight text-zinc-900">{title}</h1>
      {description && <p className="text-sm text-zinc-500 mt-1">{description}</p>}
    </div>
    {children && <div className="flex items-center gap-2 shrink-0">{children}</div>}
  </div>
);

// ---- Pagination ------------------------------------------------------------
const Pagination = ({ page, pages, total, limit, onChange }) => {
  const from = total === 0 ? 0 : (page - 1) * limit + 1;
  const to = Math.min(total, page * limit);
  return (
    <div className="flex items-center justify-between px-4 py-3 border-t border-zinc-100 text-sm text-zinc-600">
      <div className="tnum">Showing <span className="text-zinc-900 font-medium">{from}–{to}</span> of <span className="text-zinc-900 font-medium">{total.toLocaleString()}</span></div>
      <div className="flex items-center gap-1">
        <Button variant="outline" size="icon-sm" onClick={() => onChange(Math.max(1, page - 1))} disabled={page <= 1}>
          <IconChevronLeft />
        </Button>
        <div className="px-3 text-sm tnum">Page {page} of {pages}</div>
        <Button variant="outline" size="icon-sm" onClick={() => onChange(Math.min(pages, page + 1))} disabled={page >= pages}>
          <IconChevronRight />
        </Button>
      </div>
    </div>
  );
};

// ---- Avatar (initials) -----------------------------------------------------
const Avatar = ({ name, size = 'md', className = '' }) => {
  const initials = (name || '?').split(/\s+/).map(w => w[0]).slice(0, 2).join('').toUpperCase();
  const sizes = { sm: 'w-7 h-7 text-[10px]', md: 'w-8 h-8 text-xs', lg: 'w-12 h-12 text-sm' };
  // deterministic muted bg from name
  const hues = ['bg-zinc-200 text-zinc-700', 'bg-amber-100 text-amber-800', 'bg-emerald-100 text-emerald-800', 'bg-blue-100 text-blue-800', 'bg-violet-100 text-violet-800', 'bg-rose-100 text-rose-800'];
  const h = (name || '').split('').reduce((a, c) => a + c.charCodeAt(0), 0) % hues.length;
  return (
    <div className={cx('inline-flex items-center justify-center rounded-full font-semibold', hues[h], sizes[size], className)}>
      {initials}
    </div>
  );
};

// ---- Empty state -----------------------------------------------------------
const EmptyState = ({ icon: I = IconFile, title, description, action }) => (
  <div className="flex flex-col items-center justify-center text-center py-16 px-6">
    <div className="w-12 h-12 rounded-full bg-zinc-100 flex items-center justify-center text-zinc-500 mb-4">
      <I className="w-5 h-5" />
    </div>
    <div className="text-sm font-medium text-zinc-900">{title}</div>
    {description && <div className="text-sm text-zinc-500 mt-1 max-w-sm">{description}</div>}
    {action && <div className="mt-4">{action}</div>}
  </div>
);

Object.assign(window, {
  cx, Button, Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter,
  Badge, Input, Textarea, Label, Select, Switch,
  Table, THead, TBody, TR, Tabs,
  Dialog, DialogHeader, DialogBody, DialogFooter,
  Skeleton, ToastProvider, useToast,
  PageHeader, Pagination, Avatar, EmptyState,
});
// Real API integration + lightweight reactive store.
// Mock data is kept only as fallback / initial state while API loads.

// ---- formatters ------------------------------------------------------------
const formatUZS = (n) => {
  if (n == null) return '—';
  if (n >= 1_000_000_000) return `${(n / 1_000_000_000).toFixed(2)}B UZS`;
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M UZS`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(0)}K UZS`;
  return `${n.toLocaleString()} UZS`;
};
const formatNum = (n) => (n ?? 0).toLocaleString();
const formatMs = (ms) => {
  if (ms == null) return '—';
  if (ms < 1000) return `${Math.round(ms)} ms`;
  return `${(ms / 1000).toFixed(1)} s`;
};
const formatDate = (d, opts = {}) => {
  if (!d) return '—';
  const date = d instanceof Date ? d : new Date(d);
  const o = { month: 'short', day: 'numeric', year: 'numeric', ...opts };
  return date.toLocaleDateString('en-US', o);
};
const formatDateShort = (d) => {
  if (!d) return '—';
  const date = d instanceof Date ? d : new Date(d);
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
};
const formatRelative = (d) => {
  if (!d) return '—';
  const date = d instanceof Date ? d : new Date(d);
  const diff = (Date.now() - date.getTime()) / 1000;
  if (diff < 60) return 'just now';
  if (diff < 3600) return `${Math.floor(diff / 60)} min ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)} h ago`;
  if (diff < 86400 * 7) return `${Math.floor(diff / 86400)} d ago`;
  return formatDateShort(date);
};

// ---- Notification templates (static, no API) --------------------------------
const TEMPLATES = [
  { slug: 'quiz_ready', name: 'Quiz ready', description: 'Sent when an AI-imported quiz is ready to play.', is_active: true,
    text_uz: '✅ Quizingiz tayyor! "{quiz_title}" — {questions} ta savol.',
    text_ru: '✅ Ваш тест готов! «{quiz_title}» — {questions} вопросов.',
    text_en: '✅ Your quiz is ready! "{quiz_title}" — {questions} questions.' },
  { slug: 'daily_reminder', name: 'Daily reminder', description: "Reminder for users who haven't played in 24h.", is_active: true,
    text_uz: "👋 {first_name}, bugun bir quiz ishlab qo'ying!",
    text_ru: '👋 {first_name}, реши хотя бы один тест сегодня!',
    text_en: '👋 {first_name}, solve at least one quiz today!' },
  { slug: 'subscription_expiring', name: 'Subscription expiring', description: 'Sent 3 days before subscription ends.', is_active: true,
    text_uz: '⚠️ Obunangiz {days} kun ichida tugaydi.',
    text_ru: '⚠️ Ваша подписка истекает через {days} дн.',
    text_en: '⚠️ Your subscription expires in {days} days.' },
  { slug: 'import_failed', name: 'Import failed', description: 'Sent when AI import fails.', is_active: true,
    text_uz: '❌ "{file_name}" faylini qayta ishlay olmadik. Sabab: {reason}',
    text_ru: '❌ Не удалось обработать «{file_name}». Причина: {reason}',
    text_en: "❌ We couldn't process \"{file_name}\". Reason: {reason}" },
  { slug: 'welcome', name: 'Welcome message', description: 'First message on /start.', is_active: true,
    text_uz: "Quizly'ga xush kelibsiz, {first_name}! 🎉",
    text_ru: 'Добро пожаловать в Quizly, {first_name}! 🎉',
    text_en: 'Welcome to Quizly, {first_name}! 🎉' },
  { slug: 'payment_success', name: 'Payment success', description: 'Confirmation after successful payment.', is_active: false,
    text_uz: "💳 To'lov qabul qilindi. Rahmat!",
    text_ru: '💳 Платёж получен. Спасибо!',
    text_en: '💳 Payment received. Thank you!' },
];

// ---- Initial empty state ---------------------------------------------------
const EMPTY_OVERVIEW = {
  users: { total: 0, new_today: 0, new_this_week: 0, active_this_week: 0, blocked: 0 },
  quizzes: { total: 0, public: 0, private: 0, new_this_week: 0 },
  subscriptions: { active: 0 },
  revenue: { total_uzs: 0, this_month_uzs: 0 },
};

// ---- Store -----------------------------------------------------------------
function createStore(initial) {
  let state = initial;
  const listeners = new Set();
  return {
    get: () => state,
    set: (updater) => {
      state = typeof updater === 'function' ? updater(state) : updater;
      listeners.forEach(l => l());
    },
    subscribe: (l) => { listeners.add(l); return () => listeners.delete(l); },
  };
}

const store = createStore({
  users: [],
  quizzes: [],
  importLogs: [],
  notifications: [],
  templates: TEMPLATES,
  settings: {},
  admins: [],
  overview: EMPTY_OVERVIEW,
  growth30: [],
  revenue30: [],
  importBreakdown: [],
  _loading: false,
  _loaded: false,
  _error: null,
});

const useStore = (selector = (s) => s) =>
  React.useSyncExternalStore(store.subscribe, () => selector(store.get()));

// ---- Real API ---------------------------------------------------------------
const _origin = window.location.origin;
const _path = window.location.pathname; // e.g. /admin/
const _prefix = _path.startsWith('/admin') ? '/admin' : '';
const API_BASE = _origin + _prefix;

async function apiFetch(path, options = {}) {
  const token = localStorage.getItem('admin_token') || '';
  const res = await fetch(API_BASE + path, {
    ...options,
    headers: {
      'X-Admin-Token': token,
      'Content-Type': 'application/json',
      ...(options.headers || {}),
    },
  });
  if (!res.ok) throw new Error(`${res.status} ${path}`);
  return res.json();
}

async function loadRealData() {
  if (store.get()._loading || store.get()._loaded) return;
  store.set(s => ({ ...s, _loading: true, _error: null }));
  try {
    const [overview, growth, imports, settings, admins] = await Promise.allSettled([
      apiFetch('/analytics/overview'),
      apiFetch('/analytics/growth?days=30'),
      apiFetch('/analytics/imports'),
      apiFetch('/settings'),
      apiFetch('/admins'),
    ]);

    const updates = {};

    if (overview.status === 'fulfilled') {
      updates.overview = overview.value;
    }

    if (growth.status === 'fulfilled' && growth.value.data) {
      updates.growth30 = growth.value.data.map(d => ({
        date: d.date,
        new_users: d.new_users || 0,
        new_quizzes: d.new_quizzes || 0,
      }));
    }

    if (imports.status === 'fulfilled') {
      updates.importBreakdown = imports.value.breakdown || [];
    }

    if (settings.status === 'fulfilled') {
      updates.settings = settings.value;
    }

    if (admins.status === 'fulfilled') {
      updates.admins = admins.value.admins || admins.value || [];
    }

    store.set(s => ({ ...s, ...updates, _loading: false, _loaded: true }));
  } catch (e) {
    store.set(s => ({ ...s, _loading: false, _error: e.message }));
  }
}

Object.assign(window, {
  store, useStore, loadRealData, apiFetch,
  formatUZS, formatNum, formatMs, formatDate, formatDateShort, formatRelative,
});
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
// App layout: dark sidebar + topbar + content area.

const NAV_ITEMS = [
  { key: 'dashboard',     label: 'Dashboard',     path: '/',               icon: IconLayoutDashboard },
  { key: 'users',         label: 'Users',         path: '/users',          icon: IconUsers },
  { key: 'quizzes',       label: 'Quizzes',       path: '/quizzes',        icon: IconBookOpen },
  { key: 'import-logs',   label: 'Import logs',   path: '/import-logs',    icon: IconFileImport },
  { key: 'notifications', label: 'Notifications', path: '/notifications',  icon: IconBell },
  { key: 'templates',     label: 'Templates',     path: '/templates',      icon: IconMessageSquare },
  { key: 'settings',      label: 'Settings',      path: '/settings',       icon: IconSettings },
];

const Sidebar = ({ path, onNavigate, onLogout, tweaks }) => {
  const dark = tweaks.sidebar !== 'light';
  const styleBase = dark
    ? 'bg-zinc-950 text-zinc-300 border-r border-zinc-900'
    : 'bg-white text-zinc-700 border-r border-zinc-200';
  const itemActive = dark
    ? 'bg-zinc-800/70 text-white'
    : 'bg-zinc-100 text-zinc-900';
  const itemHover = dark
    ? 'hover:bg-zinc-900 hover:text-white'
    : 'hover:bg-zinc-50 hover:text-zinc-900';

  return (
    <aside className={cx('w-60 shrink-0 flex flex-col', styleBase)}>
      <div className="px-5 h-14 flex items-center gap-2 border-b border-zinc-900/60" style={!dark ? { borderColor: 'rgb(228 228 231)' } : null}>
        <div className="w-7 h-7 rounded-md flex items-center justify-center" style={{ background: dark ? 'white' : 'rgb(24 24 27)' }}>
          <span className={cx('font-bold text-sm', dark ? 'text-zinc-950' : 'text-white')}>Q</span>
        </div>
        <div>
          <div className={cx('text-sm font-semibold', dark ? 'text-white' : 'text-zinc-900')}>Quizly</div>
          <div className="text-[10px] uppercase tracking-wider text-zinc-500">Admin</div>
        </div>
      </div>
      <nav className="flex-1 px-3 py-4 space-y-0.5">
        {NAV_ITEMS.map((it) => {
          const I = it.icon;
          const active = (it.path === '/' && path === '/') || (it.path !== '/' && path.startsWith(it.path));
          return (
            <button
              key={it.key}
              onClick={() => onNavigate(it.path)}
              className={cx(
                'w-full flex items-center gap-3 px-3 h-9 rounded-md text-sm font-medium transition',
                active ? itemActive : cx('text-zinc-400', itemHover),
              )}
            >
              <I className="w-4 h-4 shrink-0" />
              <span className="flex-1 text-left">{it.label}</span>
            </button>
          );
        })}
      </nav>
      <div className={cx('p-3 border-t', dark ? 'border-zinc-900' : 'border-zinc-200')}>
        <div className={cx('flex items-center gap-3 px-2 py-2 rounded-md', dark ? 'bg-zinc-900/50' : 'bg-zinc-50')}>
          <Avatar name="Farrukh Karimov" size="md" />
          <div className="flex-1 min-w-0">
            <div className={cx('text-sm font-medium truncate', dark ? 'text-white' : 'text-zinc-900')}>Farrukh K.</div>
            <div className="text-xs text-zinc-500 truncate">owner</div>
          </div>
          <button onClick={onLogout} title="Sign out" className={cx('p-1.5 rounded-md', dark ? 'text-zinc-400 hover:bg-zinc-800' : 'text-zinc-500 hover:bg-zinc-100')}>
            <IconLogout className="w-4 h-4" />
          </button>
        </div>
      </div>
    </aside>
  );
};

const Topbar = ({ path, onOpenCmd }) => {
  const current = NAV_ITEMS.find(n => (n.path === '/' && path === '/') || (n.path !== '/' && path.startsWith(n.path)));
  return (
    <header className="h-14 border-b border-zinc-200 bg-white/80 backdrop-blur px-6 flex items-center gap-4 sticky top-0 z-30">
      <div className="flex items-center gap-2 text-sm">
        <span className="text-zinc-400">Admin</span>
        <IconChevronRight className="w-3.5 h-3.5 text-zinc-400" />
        <span className="font-medium text-zinc-900">{current ? current.label : '—'}</span>
      </div>
      <div className="flex-1" />
      <button
        onClick={onOpenCmd}
        className="hidden md:inline-flex items-center gap-2 h-9 px-3 rounded-md border border-zinc-200 bg-white text-sm text-zinc-500 hover:bg-zinc-50"
      >
        <IconSearch className="w-3.5 h-3.5" />
        <span>Search…</span>
        <span className="ml-6 text-[11px] font-mono bg-zinc-100 text-zinc-500 rounded px-1.5 py-0.5">⌘K</span>
      </button>
      <div className="flex items-center gap-1">
        <Button variant="ghost" size="icon">
          <IconBell className="w-4 h-4" />
        </Button>
        <Badge tone="green" dot>API live</Badge>
      </div>
    </header>
  );
};

// Command palette
const CommandPalette = ({ open, onClose, onNavigate }) => {
  const [q, setQ] = React.useState('');
  React.useEffect(() => { if (open) setQ(''); }, [open]);
  const items = [
    ...NAV_ITEMS.map(n => ({ kind: 'nav', label: `Go to ${n.label}`, icon: n.icon, action: () => { onNavigate(n.path); onClose(); } })),
    { kind: 'action', label: 'Send broadcast…', icon: IconSend, action: () => { onNavigate('/notifications'); onClose(); } },
    { kind: 'action', label: 'Add admin…', icon: IconShield, action: () => { onNavigate('/settings'); onClose(); } },
    { kind: 'action', label: 'View import logs', icon: IconFileImport, action: () => { onNavigate('/import-logs'); onClose(); } },
  ];
  const filtered = q ? items.filter(it => it.label.toLowerCase().includes(q.toLowerCase())) : items;
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-24 anim-fade">
      <div className="absolute inset-0 bg-zinc-950/40" onClick={onClose} />
      <div className="relative w-full max-w-lg mx-4 rounded-xl border border-zinc-200 bg-white shadow-pop overflow-hidden anim-pop">
        <div className="flex items-center border-b border-zinc-200 px-3">
          <IconSearch className="w-4 h-4 text-zinc-400" />
          <input
            autoFocus
            value={q}
            onChange={e => setQ(e.target.value)}
            placeholder="Type a command or search…"
            className="flex-1 h-12 px-3 bg-transparent outline-none text-sm placeholder:text-zinc-400"
          />
          <kbd className="text-[11px] font-mono bg-zinc-100 text-zinc-500 rounded px-1.5 py-0.5">esc</kbd>
        </div>
        <div className="max-h-72 overflow-y-auto py-2">
          {filtered.length === 0 ? (
            <div className="text-sm text-zinc-500 px-4 py-6 text-center">No results.</div>
          ) : (
            filtered.map((it, i) => {
              const I = it.icon;
              return (
                <button key={i} onClick={it.action} className="w-full flex items-center gap-3 px-3 py-2 text-sm hover:bg-zinc-100 text-zinc-900">
                  <I className="w-4 h-4 text-zinc-500" />
                  <span className="flex-1 text-left">{it.label}</span>
                  <IconChevronRight className="w-3.5 h-3.5 text-zinc-400" />
                </button>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
};

Object.assign(window, { NAV_ITEMS, Sidebar, Topbar, CommandPalette });
// Login page — token input + remember + demo helper.

const LoginPage = ({ onLogin }) => {
  const [token, setToken] = React.useState('');
  const [show, setShow] = React.useState(false);
  const [remember, setRemember] = React.useState(true);
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState('');

  const submit = (e) => {
    e.preventDefault();
    setError('');
    if (token.trim().length < 6) {
      setError('Token looks too short. Paste the full admin token.');
      return;
    }
    setLoading(true);
    setTimeout(() => {
      setLoading(false);
      onLogin(token.trim(), remember);
    }, 700);
  };

  return (
    <div className="min-h-screen grid grid-cols-1 md:grid-cols-2 bg-zinc-50">
      {/* Left — branding panel */}
      <div className="hidden md:flex flex-col justify-between bg-zinc-950 text-white p-10 relative overflow-hidden">
        <div className="absolute inset-0 bg-dot opacity-10" />
        <div className="relative flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-white text-zinc-950 font-bold flex items-center justify-center text-base">Q</div>
          <span className="font-semibold">Quizly</span>
          <Badge tone="dark" className="ml-2 border-zinc-700">admin</Badge>
        </div>
        <div className="relative">
          <div className="text-xs uppercase tracking-widest text-zinc-400 mb-3">Today's pulse</div>
          <div className="text-4xl font-semibold tracking-tight">+47 <span className="text-zinc-400 text-2xl font-normal">new users today</span></div>
          <div className="mt-8 grid grid-cols-3 gap-6 max-w-md">
            <div>
              <div className="text-2xl font-semibold tnum">1,467</div>
              <div className="text-xs text-zinc-400">Total users</div>
            </div>
            <div>
              <div className="text-2xl font-semibold tnum">826</div>
              <div className="text-xs text-zinc-400">Total quizzes</div>
            </div>
            <div>
              <div className="text-2xl font-semibold tnum">211</div>
              <div className="text-xs text-zinc-400">Active subs</div>
            </div>
          </div>
        </div>
        <div className="relative text-xs text-zinc-500">
          v2.4.1 · <span className="text-zinc-400">API <span className="font-mono">http://localhost:8004</span></span>
        </div>
      </div>

      {/* Right — form */}
      <div className="flex items-center justify-center p-8">
        <div className="w-full max-w-sm">
          <div className="md:hidden flex items-center gap-2 mb-8">
            <div className="w-8 h-8 rounded-lg bg-zinc-950 text-white font-bold flex items-center justify-center">Q</div>
            <span className="font-semibold">Quizly admin</span>
          </div>
          <h1 className="text-2xl font-semibold tracking-tight">Sign in</h1>
          <p className="text-sm text-zinc-500 mt-1">Paste your admin token to continue.</p>

          <form onSubmit={submit} className="mt-8 space-y-4">
            <div>
              <Label htmlFor="token">Admin token</Label>
              <div className="mt-1.5 relative">
                <Input
                  id="token"
                  type={show ? 'text' : 'password'}
                  placeholder="qzly_••••••••••••••••"
                  leftIcon={<IconKey className="w-4 h-4" />}
                  value={token}
                  onChange={e => setToken(e.target.value)}
                />
                <button type="button" onClick={() => setShow(!show)} className="absolute right-2 top-1/2 -translate-y-1/2 p-1.5 text-zinc-500 hover:text-zinc-900">
                  {show ? <IconEyeOff className="w-4 h-4" /> : <IconEye className="w-4 h-4" />}
                </button>
              </div>
              {error && <div className="text-xs text-red-600 mt-1.5">{error}</div>}
            </div>

            <label className="flex items-center gap-2 text-sm text-zinc-600 cursor-pointer">
              <input type="checkbox" checked={remember} onChange={e => setRemember(e.target.checked)} className="rounded border-zinc-300" />
              Remember me on this device
            </label>

            <Button type="submit" className="w-full" disabled={loading}>
              {loading ? <IconLoader className="w-4 h-4 animate-spin" /> : <IconLock className="w-4 h-4" />}
              {loading ? 'Verifying…' : 'Sign in'}
            </Button>

            <button
              type="button"
              onClick={() => setToken('qzly_demo_token_2026_xxxxxxxxxxxxxxxx')}
              className="w-full text-xs text-zinc-500 hover:text-zinc-900"
            >
              Use demo token →
            </button>
          </form>

          <div className="mt-10 text-xs text-zinc-500">
            Token is stored as <span className="font-mono text-zinc-700">admin_token</span> in localStorage and attached via the
            <span className="font-mono text-zinc-700"> X-Admin-Token</span> header on every request.
          </div>
        </div>
      </div>
    </div>
  );
};

Object.assign(window, { LoginPage });
// Dashboard — overview cards + charts (real API)

const StatCard = ({ icon: I, label, value, sub, trend, spark, color = 'rgb(24 24 27)' }) => (
  <Card>
    <CardContent className="pt-6 pb-6">
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-2 text-zinc-500 text-sm">
          {I && <I className="w-4 h-4" />}
          <span>{label}</span>
        </div>
        {trend != null && (
          <Badge tone={trend >= 0 ? 'green' : 'red'} className="!py-0.5">
            {trend >= 0 ? <IconTrendUp className="w-3 h-3" /> : <IconTrendDown className="w-3 h-3" />}
            {trend >= 0 ? '+' : ''}{trend}%
          </Badge>
        )}
      </div>
      <div className="mt-4 flex items-end justify-between gap-3">
        <div>
          <div className="text-3xl font-semibold tracking-tight tnum">{value}</div>
          {sub && <div className="text-xs text-zinc-500 mt-1">{sub}</div>}
        </div>
        {spark && spark.length > 0 && <Sparkline data={spark} color={color} width={84} height={28} />}
      </div>
    </CardContent>
  </Card>
);

const DashboardPage = () => {
  const [overview, setOverview] = React.useState(null);
  const [growth, setGrowth] = React.useState([]);
  const [importBreakdown, setImportBreakdown] = React.useState([]);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState(null);
  const [range, setRange] = React.useState('30');

  React.useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    Promise.allSettled([
      apiFetch('/analytics/overview'),
      apiFetch('/analytics/growth?days=30'),
      apiFetch('/analytics/imports'),
    ]).then(([ovRes, grRes, impRes]) => {
      if (cancelled) return;
      if (ovRes.status === 'fulfilled') setOverview(ovRes.value);
      else setError('Overview yuklanmadi: ' + ovRes.reason?.message);

      if (grRes.status === 'fulfilled' && grRes.value.data) {
        setGrowth(grRes.value.data.map(d => ({
          date: d.date,
          new_users: d.new_users || 0,
          new_quizzes: d.new_quizzes || 0,
        })));
      }

      if (impRes.status === 'fulfilled') {
        setImportBreakdown(impRes.value.breakdown || []);
      }

      setLoading(false);
    });

    return () => { cancelled = true; };
  }, []);

  if (loading) {
    return (
      <div className="p-8 max-w-[1400px] mx-auto">
        <PageHeader title="Dashboard" description="Live overview of users, quizzes and revenue." />
        <div className="flex items-center justify-center h-64 text-zinc-400 text-sm gap-2">
          <IconLoader className="w-5 h-5 animate-spin" />
          Yuklanmoqda...
        </div>
      </div>
    );
  }

  if (error || !overview) {
    return (
      <div className="p-8 max-w-[1400px] mx-auto">
        <PageHeader title="Dashboard" description="Live overview of users, quizzes and revenue." />
        <div className="flex flex-col items-center justify-center h-64 gap-3">
          <div className="text-red-600 text-sm">{error || "Ma'lumot yuklanmadi"}</div>
          <Button variant="outline" onClick={() => window.location.reload()}>Qayta urinish</Button>
        </div>
      </div>
    );
  }

  const days = parseInt(range, 10);
  const growthSlice = growth.slice(-days);

  const users = overview.users || {};
  const quizzes = overview.quizzes || {};
  const subscriptions = overview.subscriptions || {};
  const revenue = overview.revenue || {};

  return (
    <div className="p-8 max-w-[1400px] mx-auto">
      <PageHeader
        title="Dashboard"
        description="Live overview of users, quizzes and revenue."
      >
        <div className="flex items-center gap-2">
          <Tabs
            value={range}
            onChange={setRange}
            items={[
              { value: '7', label: '7d' },
              { value: '14', label: '14d' },
              { value: '30', label: '30d' },
            ]}
          />
        </div>
      </PageHeader>

      {/* Stat row */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4 mb-6">
        <StatCard
          icon={IconUsers}
          label="Total users"
          value={(users.total || 0).toLocaleString()}
          sub={
            <>
              <span className="text-emerald-600 font-medium">+{users.new_today || 0}</span> bugun
              {users.active_this_week != null && <> · {(users.active_this_week).toLocaleString()} haftalik aktiv</>}
            </>
          }
          spark={growthSlice.map(g => g.new_users)}
          color="rgb(24 24 27)"
        />
        <StatCard
          icon={IconBookOpen}
          label="Total quizzes"
          value={(quizzes.total || 0).toLocaleString()}
          sub={<>{(quizzes.public || 0).toLocaleString()} ommaviy · {(quizzes.private || 0).toLocaleString()} shaxsiy</>}
          spark={growthSlice.map(g => g.new_quizzes)}
          color="rgb(59 130 246)"
        />
        <StatCard
          icon={IconActivity}
          label="Active subscriptions"
          value={(subscriptions.active || 0).toLocaleString()}
          sub={
            users.total > 0
              ? <>{(((subscriptions.active || 0) / users.total) * 100).toFixed(1)}% konversiya</>
              : null
          }
          color="rgb(16 185 129)"
        />
        <StatCard
          icon={IconWallet}
          label="Revenue (this month)"
          value={formatUZS(revenue.this_month_uzs)}
          sub={<>Jami {formatUZS(revenue.total_uzs)}</>}
          color="rgb(245 158 11)"
        />
      </div>

      {/* Charts row */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-4 mb-6">
        <Card className="xl:col-span-2">
          <CardHeader>
            <div className="flex items-start justify-between">
              <div>
                <CardTitle>O'sish</CardTitle>
                <CardDescription>Kunlik yangi foydalanuvchilar va quizlar</CardDescription>
              </div>
              <div className="text-right">
                <div className="text-2xl font-semibold tnum">
                  {growthSlice.reduce((a, g) => a + g.new_users, 0)}
                </div>
                <div className="text-xs text-zinc-500">yangi foydalanuvchi · {days}k</div>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            {growthSlice.length > 0 ? (
              <LineChart
                data={growthSlice}
                height={260}
                series={[
                  { key: 'new_users',   label: 'Foydalanuvchilar', color: 'rgb(24 24 27)' },
                  { key: 'new_quizzes', label: 'Quizlar',          color: 'rgb(59 130 246)' },
                ]}
              />
            ) : (
              <div className="h-[260px] flex items-center justify-center text-zinc-400 text-sm">
                Ma'lumot yo'q
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Import holati</CardTitle>
            <CardDescription>Fayl turlari bo'yicha</CardDescription>
          </CardHeader>
          <CardContent className="px-0 pb-0">
            {importBreakdown.length === 0 ? (
              <div className="px-6 py-8 text-zinc-400 text-sm text-center">Ma'lumot yo'q</div>
            ) : (
              <ul className="divide-y divide-zinc-100">
                {(() => {
                  const grouped = {};
                  importBreakdown.forEach(b => {
                    if (!grouped[b.file_type]) grouped[b.file_type] = { ok: 0, fail: 0, pending: 0, ms: 0, msCount: 0 };
                    const g = grouped[b.file_type];
                    if (b.status === 'completed') g.ok += b.count;
                    else if (b.status === 'failed') g.fail += b.count;
                    else g.pending += b.count;
                    if (b.avg_processing_ms) { g.ms += b.avg_processing_ms * b.count; g.msCount += b.count; }
                  });
                  return Object.entries(grouped).map(([ft, v]) => {
                    const total = v.ok + v.fail + v.pending;
                    const okPct = total > 0 ? (v.ok / total) * 100 : 0;
                    const failPct = total > 0 ? (v.fail / total) * 100 : 0;
                    const avgMs = v.msCount ? v.ms / v.msCount : 0;
                    return (
                      <li key={ft} className="px-6 py-4">
                        <div className="flex items-center justify-between mb-2">
                          <div className="flex items-center gap-2">
                            <span className="uppercase font-mono text-xs bg-zinc-100 text-zinc-700 rounded px-1.5 py-0.5">{ft}</span>
                            <span className="text-sm text-zinc-900 font-medium">{total} fayl</span>
                          </div>
                          <div className="text-xs text-zinc-500 tnum">o'rtacha {formatMs(avgMs)}</div>
                        </div>
                        <div className="h-1.5 w-full rounded-full bg-zinc-100 overflow-hidden flex">
                          <div className="h-full bg-emerald-500" style={{ width: `${okPct}%` }} />
                          <div className="h-full bg-red-400" style={{ width: `${failPct}%` }} />
                        </div>
                        <div className="flex items-center gap-3 mt-2 text-xs text-zinc-500">
                          <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-emerald-500" /> {v.ok} ok</span>
                          {v.fail > 0 && <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-red-400" /> {v.fail} xato</span>}
                          {v.pending > 0 && <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-amber-400" /> {v.pending} kutilmoqda</span>}
                        </div>
                      </li>
                    );
                  });
                })()}
              </ul>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Stats summary row */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">
        <Card className="xl:col-span-2">
          <CardHeader>
            <CardTitle>Statistika xulosasi</CardTitle>
            <CardDescription>Hozirgi holat</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
              <div className="rounded-lg border border-zinc-200 p-4">
                <div className="text-xs text-zinc-500">Bugungi yangi</div>
                <div className="text-2xl font-semibold tnum mt-1 text-emerald-600">+{users.new_today || 0}</div>
                <div className="text-xs text-zinc-500 mt-0.5">foydalanuvchi</div>
              </div>
              <div className="rounded-lg border border-zinc-200 p-4">
                <div className="text-xs text-zinc-500">Haftalik yangi</div>
                <div className="text-2xl font-semibold tnum mt-1">+{users.new_this_week || 0}</div>
                <div className="text-xs text-zinc-500 mt-0.5">foydalanuvchi</div>
              </div>
              <div className="rounded-lg border border-zinc-200 p-4">
                <div className="text-xs text-zinc-500">Bloklangan</div>
                <div className="text-2xl font-semibold tnum mt-1 text-red-600">{users.blocked || 0}</div>
                <div className="text-xs text-zinc-500 mt-0.5">foydalanuvchi</div>
              </div>
              <div className="rounded-lg border border-zinc-200 p-4">
                <div className="text-xs text-zinc-500">Haftalik quiz</div>
                <div className="text-2xl font-semibold tnum mt-1">+{quizzes.new_this_week || 0}</div>
                <div className="text-xs text-zinc-500 mt-0.5">yangi quiz</div>
              </div>
              <div className="rounded-lg border border-zinc-200 p-4">
                <div className="text-xs text-zinc-500">Jami daromad</div>
                <div className="text-xl font-semibold tnum mt-1">{formatUZS(revenue.total_uzs)}</div>
                <div className="text-xs text-zinc-500 mt-0.5">barcha vaqt</div>
              </div>
              <div className="rounded-lg border border-zinc-200 p-4">
                <div className="text-xs text-zinc-500">Bu oy</div>
                <div className="text-xl font-semibold tnum mt-1 text-emerald-600">{formatUZS(revenue.this_month_uzs)}</div>
                <div className="text-xs text-zinc-500 mt-0.5">daromad</div>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Tezkor ma'lumot</CardTitle>
            <CardDescription>Asosiy ko'rsatkichlar</CardDescription>
          </CardHeader>
          <CardContent className="px-0 pb-0">
            <ul className="divide-y divide-zinc-100">
              {[
                { label: 'Jami foydalanuvchilar', value: (users.total || 0).toLocaleString(), icon: IconUsers, color: 'text-zinc-700' },
                { label: 'Jami quizlar', value: (quizzes.total || 0).toLocaleString(), icon: IconBookOpen, color: 'text-blue-600' },
                { label: 'Faol obunalar', value: (subscriptions.active || 0).toLocaleString(), icon: IconActivity, color: 'text-emerald-600' },
                { label: 'Ommaviy quizlar', value: (quizzes.public || 0).toLocaleString(), icon: IconEye, color: 'text-amber-600' },
                { label: 'Shaxsiy quizlar', value: (quizzes.private || 0).toLocaleString(), icon: IconEyeOff, color: 'text-zinc-500' },
              ].map((row, i) => {
                const I = row.icon;
                return (
                  <li key={i} className="flex items-center gap-3 px-6 py-3">
                    <I className={cx('w-4 h-4 shrink-0', row.color)} />
                    <div className="flex-1 text-sm text-zinc-700">{row.label}</div>
                    <div className="text-sm font-semibold tnum text-zinc-900">{row.value}</div>
                  </li>
                );
              })}
            </ul>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

Object.assign(window, { DashboardPage });
// Users page — server-side pagination + search, real API

const PAGE_LIMIT = 20;

const UsersPage = () => {
  const [users, setUsers] = React.useState([]);
  const [total, setTotal] = React.useState(0);
  const [page, setPage] = React.useState(1);
  const [search, setSearch] = React.useState('');
  const [searchInput, setSearchInput] = React.useState('');
  const [filter, setFilter] = React.useState('all'); // all | blocked
  const [selected, setSelected] = React.useState(null);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState(null);
  const toast = useToast();

  const fetchUsers = React.useCallback((pg, srch, flt) => {
    setLoading(true);
    setError(null);
    const offset = (pg - 1) * PAGE_LIMIT;
    let url = `/users?limit=${PAGE_LIMIT}&offset=${offset}`;
    if (srch) url += `&search=${encodeURIComponent(srch)}`;
    if (flt === 'blocked') url += `&is_blocked=true`;

    apiFetch(url)
      .then(data => {
        const list = data.users || data || [];
        // Normalize field names: API returns is_bot_blocked, we use is_blocked
        const normalized = list.map(u => ({
          ...u,
          is_blocked: u.is_blocked ?? u.is_bot_blocked ?? false,
        }));
        setUsers(normalized);
        setTotal(data.total ?? normalized.length);
        setLoading(false);
      })
      .catch(err => {
        setError(err.message);
        setLoading(false);
      });
  }, []);

  React.useEffect(() => {
    fetchUsers(page, search, filter);
  }, [page, search, filter]);

  // Debounce search input
  React.useEffect(() => {
    const t = setTimeout(() => {
      setSearch(searchInput);
      setPage(1);
    }, 400);
    return () => clearTimeout(t);
  }, [searchInput]);

  const handleFilterChange = (f) => {
    setFilter(f);
    setPage(1);
  };

  const pages = Math.max(1, Math.ceil(total / PAGE_LIMIT));

  const toggleBlock = (u) => {
    apiFetch(`/users/${u.id}/block`, { method: 'PATCH' })
      .then(res => {
        const newStatus = res.is_bot_blocked;
        setUsers(prev => prev.map(x => x.id === u.id ? { ...x, is_blocked: newStatus } : x));
        if (selected && selected.id === u.id) setSelected(s => ({ ...s, is_blocked: newStatus }));
        toast.success(newStatus ? `${u.first_name || 'User'} bloklandi` : `${u.first_name || 'User'} blokdan chiqarildi`);
      })
      .catch(() => toast.error('Amal bajarilmadi'));
  };

  const displayName = (u) => [u.first_name, u.last_name].filter(Boolean).join(' ') || `id${u.telegram_id}`;

  return (
    <div className="p-8 max-w-[1400px] mx-auto">
      <PageHeader
        title="Foydalanuvchilar"
        description={
          loading
            ? 'Yuklanmoqda...'
            : <><span className="tnum">{total.toLocaleString()}</span> ta foydalanuvchi</>
        }
      />

      <Card>
        <div className="flex items-center gap-3 p-4 border-b border-zinc-100 flex-wrap">
          <Input
            placeholder="Ism, username yoki Telegram ID bo&#39;yicha qidiring…"
            value={searchInput}
            onChange={e => setSearchInput(e.target.value)}
            leftIcon={<IconSearch className="w-4 h-4" />}
            className="max-w-sm"
          />
          <Tabs
            value={filter}
            onChange={handleFilterChange}
            items={[
              { value: 'all',     label: 'Barchasi' },
              { value: 'blocked', label: 'Bloklangan' },
            ]}
          />
          <div className="flex-1" />
          {!loading && (
            <div className="text-xs text-zinc-500 tnum">{total} natija</div>
          )}
        </div>

        {loading ? (
          <div className="flex items-center justify-center h-48 text-zinc-400 text-sm gap-2">
            <IconLoader className="w-5 h-5 animate-spin" />
            Yuklanmoqda...
          </div>
        ) : error ? (
          <div className="flex flex-col items-center justify-center h-48 gap-3">
            <div className="text-red-600 text-sm">{error}</div>
            <Button variant="outline" size="sm" onClick={() => fetchUsers(page, search, filter)}>
              Qayta urinish
            </Button>
          </div>
        ) : (
          <>
            <Table>
              <THead>
                <tr>
                  <th>Foydalanuvchi</th>
                  <th>Telegram ID</th>
                  <th>Til</th>
                  <th>Oxirgi faollik</th>
                  <th>Ro'yxatdan o'tgan</th>
                  <th>Holat</th>
                </tr>
              </THead>
              <TBody>
                {users.map((u) => (
                  <TR
                    key={u.id}
                    onClick={() => setSelected(u)}
                    className="cursor-pointer"
                  >
                    <td className="py-3">
                      <div className="flex items-center gap-3">
                        <Avatar name={displayName(u)} size="md" />
                        <div className="min-w-0">
                          <div className="text-sm font-medium text-zinc-900 truncate">
                            {displayName(u)}
                          </div>
                          <div className="text-xs text-zinc-500 truncate">
                            {u.username ? `@${u.username}` : <span className="italic">username yo'q</span>}
                          </div>
                        </div>
                      </div>
                    </td>
                    <td className="font-mono text-xs text-zinc-600 tnum">{u.telegram_id}</td>
                    <td><Badge tone="neutral">{u.language_code || '—'}</Badge></td>
                    <td className="text-sm text-zinc-600 tnum">
                      {u.last_active_at ? formatRelative(u.last_active_at) : '—'}
                    </td>
                    <td className="text-sm text-zinc-600 tnum">
                      {u.created_at ? formatDateShort(u.created_at) : '—'}
                    </td>
                    <td>
                      {u.is_blocked
                        ? <Badge tone="red" dot>bloklangan</Badge>
                        : <Badge tone="green" dot>faol</Badge>}
                    </td>
                  </TR>
                ))}
                {users.length === 0 && (
                  <tr>
                    <td colSpan={6}>
                      <EmptyState
                        icon={IconUsers}
                        title="Foydalanuvchi topilmadi"
                        description="Qidiruv yoki filtrni o&#39;zgartirib ko&#39;ring."
                      />
                    </td>
                  </tr>
                )}
              </TBody>
            </Table>

            <Pagination page={page} pages={pages} total={total} limit={PAGE_LIMIT} onChange={setPage} />
          </>
        )}
      </Card>

      <UserDetailDialog
        user={selected}
        onClose={() => setSelected(null)}
      />
    </div>
  );
};

const UserDetailDialog = ({ user, onClose }) => {
  if (!user) return null;
  const name = [user.first_name, user.last_name].filter(Boolean).join(' ') || `id${user.telegram_id}`;
  return (
    <Dialog open={!!user} onClose={onClose} maxW="max-w-2xl">
      <DialogHeader
        title={
          <div className="flex items-center gap-3">
            <Avatar name={name} size="lg" />
            <div>
              <div className="text-base font-semibold">{name}</div>
              <div className="text-xs text-zinc-500 font-normal">
                {user.username ? `@${user.username}` : "username yo'q"} · <span className="font-mono">{user.telegram_id}</span>
              </div>
            </div>
          </div>
        }
        onClose={onClose}
      />
      <DialogBody className="space-y-6">
        <div className="rounded-lg border border-zinc-200 p-4">
          <div className="text-xs uppercase tracking-wider text-zinc-500 mb-3">Hisob ma'lumotlari</div>
          <div className="grid grid-cols-2 gap-y-3 text-sm">
            <div className="text-zinc-500">Telegram ID</div>
            <div className="text-zinc-900 font-mono tnum">{user.telegram_id}</div>

            <div className="text-zinc-500">Til</div>
            <div><Badge tone="neutral">{user.language_code || '—'}</Badge></div>

            <div className="text-zinc-500">Ro'yxatdan o'tgan</div>
            <div className="text-zinc-900 tnum">
              {user.created_at ? formatDate(user.created_at) : '—'}
            </div>

            <div className="text-zinc-500">Oxirgi faollik</div>
            <div className="text-zinc-900 tnum">
              {user.last_active_at ? formatDate(user.last_active_at) : '—'}
            </div>

            <div className="text-zinc-500">Holat</div>
            <div>
              {user.is_blocked
                ? <Badge tone="red" dot>bloklangan</Badge>
                : <Badge tone="green" dot>faol</Badge>}
            </div>

            {user.is_bot_blocked != null && (
              <>
                <div className="text-zinc-500">Bot bloki</div>
                <div>
                  {user.is_bot_blocked
                    ? <Badge tone="red" dot>bot bloklangan</Badge>
                    : <Badge tone="neutral" dot>yo'q</Badge>}
                </div>
              </>
            )}
          </div>
        </div>
      </DialogBody>
      <DialogFooter>
        <Button variant="outline" onClick={onClose}>Yopish</Button>
      </DialogFooter>
    </Dialog>
  );
};

Object.assign(window, { UsersPage });
// Quizzes page — real API, server-side visibility filter + pagination

const QUIZ_LIMIT = 20;

const QuizzesPage = () => {
  const [quizzes, setQuizzes] = React.useState([]);
  const [total, setTotal] = React.useState(0);
  const [page, setPage] = React.useState(1);
  const [filter, setFilter] = React.useState('all'); // all | public | private
  const [search, setSearch] = React.useState('');
  const [searchInput, setSearchInput] = React.useState('');
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState(null);
  const [confirmDelete, setConfirmDelete] = React.useState(null);
  const toast = useToast();

  const fetchQuizzes = React.useCallback((pg, vis, srch) => {
    setLoading(true);
    setError(null);
    const offset = (pg - 1) * QUIZ_LIMIT;
    let url = `/quizzes?limit=${QUIZ_LIMIT}&offset=${offset}`;
    if (vis === 'public') url += `&visibility=public`;
    else if (vis === 'private') url += `&visibility=private`;
    if (srch) url += `&search=${encodeURIComponent(srch)}`;

    apiFetch(url)
      .then(data => {
        const list = data.quizzes || data || [];
        setQuizzes(list);
        setTotal(data.total ?? list.length);
        setLoading(false);
      })
      .catch(err => {
        setError(err.message);
        setLoading(false);
      });
  }, []);

  React.useEffect(() => {
    fetchQuizzes(page, filter, search);
  }, [page, filter, search]);

  // Debounce search
  React.useEffect(() => {
    const t = setTimeout(() => {
      setSearch(searchInput);
      setPage(1);
    }, 400);
    return () => clearTimeout(t);
  }, [searchInput]);

  const handleFilterChange = (f) => {
    setFilter(f);
    setPage(1);
  };

  const pages = Math.max(1, Math.ceil(total / QUIZ_LIMIT));

  const doDelete = (quiz) => {
    apiFetch(`/quizzes/${quiz.id}`, { method: 'DELETE' })
      .then(() => {
        setQuizzes(prev => prev.filter(q => q.id !== quiz.id));
        setTotal(t => t - 1);
        setConfirmDelete(null);
        toast.success(`"${quiz.title}" o'chirildi`);
      })
      .catch(() => toast.error("O'chirib bo'lmadi"));
  };

  const sourceLabel = {
    manual: 'Manual',
    ai_pdf: 'AI · PDF',
    ai_docx: 'AI · DOCX',
    ai_image: 'AI · Rasm',
    duplicated: 'Nusxa',
  };

  return (
    <div className="p-8 max-w-[1400px] mx-auto">
      <PageHeader
        title="Quizlar"
        description={
          loading
            ? 'Yuklanmoqda...'
            : <><span className="tnum">{total.toLocaleString()}</span> ta quiz</>
        }
      />

      <Card>
        <div className="flex items-center gap-3 p-4 border-b border-zinc-100 flex-wrap">
          <Tabs
            value={filter}
            onChange={handleFilterChange}
            items={[
              { value: 'all',     label: 'Barchasi' },
              { value: 'public',  label: 'Ommaviy' },
              { value: 'private', label: 'Shaxsiy' },
            ]}
          />
          <Input
            placeholder="Quiz nomini qidiring…"
            value={searchInput}
            onChange={e => setSearchInput(e.target.value)}
            leftIcon={<IconSearch className="w-4 h-4" />}
            className="max-w-xs"
          />
          <div className="flex-1" />
          {!loading && <div className="text-xs text-zinc-500 tnum">{total} natija</div>}
        </div>

        {loading ? (
          <div className="flex items-center justify-center h-48 text-zinc-400 text-sm gap-2">
            <IconLoader className="w-5 h-5 animate-spin" />
            Yuklanmoqda...
          </div>
        ) : error ? (
          <div className="flex flex-col items-center justify-center h-48 gap-3">
            <div className="text-red-600 text-sm">{error}</div>
            <Button variant="outline" size="sm" onClick={() => fetchQuizzes(page, filter, search)}>
              Qayta urinish
            </Button>
          </div>
        ) : (
          <>
            <Table>
              <THead>
                <tr>
                  <th>Sarlavha</th>
                  <th>Egasi</th>
                  <th className="text-right">Savollar</th>
                  <th className="text-right">O'yinlar</th>
                  <th>Ko'rinish</th>
                  <th>Manba</th>
                  <th>Yaratilgan</th>
                  <th></th>
                </tr>
              </THead>
              <TBody>
                {quizzes.map(q => (
                  <TR key={q.id}>
                    <td className="py-3">
                      <div className="text-sm font-medium text-zinc-900">{q.title}</div>
                      <div className="text-xs text-zinc-500 font-mono">#{q.id}</div>
                    </td>
                    <td>
                      <div className="text-sm text-zinc-700 font-mono">
                        {q.owner_id ? `id${q.owner_id}` : '—'}
                      </div>
                    </td>
                    <td className="text-right tnum text-sm">
                      {q.total_questions ?? q.questions_count ?? '—'}
                    </td>
                    <td className="text-right tnum text-sm">
                      {(q.play_count || 0).toLocaleString()}
                    </td>
                    <td>
                      {q.visibility === 'public'
                        ? <Badge tone="green" dot>ommaviy</Badge>
                        : <Badge tone="yellow" dot>shaxsiy</Badge>}
                    </td>
                    <td>
                      {q.source_type ? (
                        <span className="inline-flex items-center gap-1.5 text-xs text-zinc-600">
                          <span className="w-1.5 h-1.5 rounded-full bg-zinc-400" />
                          {sourceLabel[q.source_type] || q.source_type}
                        </span>
                      ) : '—'}
                    </td>
                    <td className="text-sm text-zinc-600 tnum">
                      {q.created_at ? formatDateShort(q.created_at) : '—'}
                    </td>
                    <td className="text-right" onClick={e => e.stopPropagation()}>
                      <Button variant="ghost" size="sm" onClick={() => setConfirmDelete(q)}>
                        <IconTrash className="w-3.5 h-3.5 text-red-500" />
                      </Button>
                    </td>
                  </TR>
                ))}
                {quizzes.length === 0 && (
                  <tr>
                    <td colSpan={7}>
                      <EmptyState
                        icon={IconBookOpen}
                        title="Quiz topilmadi"
                        description="Boshqa filtr yoki qidiruv so&#39;zini sinab ko&#39;ring."
                      />
                    </td>
                  </tr>
                )}
              </TBody>
            </Table>

            <Pagination page={page} pages={pages} total={total} limit={QUIZ_LIMIT} onChange={setPage} />
          </>
        )}
      </Card>
      <DeleteQuizDialog quiz={confirmDelete} onConfirm={doDelete} onClose={() => setConfirmDelete(null)} />
    </div>
  );
};

// Delete confirmation dialog
const DeleteQuizDialog = ({ quiz, onConfirm, onClose }) => {
  if (!quiz) return null;
  return (
    <Dialog open={!!quiz} onClose={onClose} maxW="max-w-md">
      <DialogHeader title="Quizni o&#39;chirish" onClose={onClose} />
      <DialogBody>
        <p className="text-sm text-zinc-700">
          <span className="font-semibold">"{quiz.title}"</span> quizini o'chirmoqchimisiz?
          Ushbu amal qaytarib bo'lmaydi.
        </p>
      </DialogBody>
      <DialogFooter>
        <Button variant="outline" onClick={onClose}>Bekor qilish</Button>
        <Button variant="destructive" onClick={() => onConfirm(quiz)}>
          <IconTrash className="w-4 h-4" /> Ha, o'chir
        </Button>
      </DialogFooter>
    </Dialog>
  );
};

Object.assign(window, { QuizzesPage });
// Import logs page — real API from analytics/imports

const ImportLogsPage = () => {
  const [breakdown, setBreakdown] = React.useState([]);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState(null);
  const [statusFilter, setStatusFilter] = React.useState('all');
  const [typeFilter, setTypeFilter] = React.useState('all');

  React.useEffect(() => {
    setLoading(true);
    setError(null);
    apiFetch('/analytics/imports')
      .then(data => {
        setBreakdown(data.breakdown || []);
        setLoading(false);
      })
      .catch(err => {
        setError(err.message);
        setLoading(false);
      });
  }, []);

  // Aggregate totals from breakdown
  const counts = React.useMemo(() => {
    const all = breakdown.reduce((s, b) => s + b.count, 0);
    const completed = breakdown.filter(b => b.status === 'completed').reduce((s, b) => s + b.count, 0);
    const failed = breakdown.filter(b => b.status === 'failed').reduce((s, b) => s + b.count, 0);
    const pending = breakdown.filter(b => b.status === 'pending').reduce((s, b) => s + b.count, 0);
    return { all, completed, failed, pending };
  }, [breakdown]);

  const fileTypes = React.useMemo(() => {
    const types = new Set(breakdown.map(b => b.file_type));
    return Array.from(types);
  }, [breakdown]);

  const filtered = React.useMemo(() => {
    return breakdown.filter(b => {
      if (statusFilter !== 'all' && b.status !== statusFilter) return false;
      if (typeFilter !== 'all' && b.file_type !== typeFilter) return false;
      return true;
    });
  }, [breakdown, statusFilter, typeFilter]);

  // Group filtered rows by file_type for display
  const grouped = React.useMemo(() => {
    const g = {};
    filtered.forEach(b => {
      if (!g[b.file_type]) g[b.file_type] = { ok: 0, fail: 0, pending: 0, ms: 0, msCount: 0, avgQuestions: [] };
      const entry = g[b.file_type];
      if (b.status === 'completed') entry.ok += b.count;
      else if (b.status === 'failed') entry.fail += b.count;
      else entry.pending += b.count;
      if (b.avg_processing_ms != null) {
        entry.ms += b.avg_processing_ms * b.count;
        entry.msCount += b.count;
      }
      if (b.avg_questions != null) entry.avgQuestions.push({ val: b.avg_questions, cnt: b.count });
    });
    return g;
  }, [filtered]);

  return (
    <div className="p-8 max-w-[1400px] mx-auto">
      <PageHeader
        title="Import loglari"
        description="AI fayl qayta ishlash statistikasi (PDF, DOCX, rasm)."
      />

      {/* Summary cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <MiniStat label="Jami" value={counts.all} tone="neutral" loading={loading} />
        <MiniStat label="Muvaffaqiyatli" value={counts.completed} tone="green" loading={loading} />
        <MiniStat label="Xato" value={counts.failed} tone="red" loading={loading} />
        <MiniStat label="Kutilmoqda" value={counts.pending} tone="yellow" loading={loading} />
      </div>

      {loading ? (
        <Card>
          <div className="flex items-center justify-center h-64 text-zinc-400 text-sm gap-2">
            <IconLoader className="w-5 h-5 animate-spin" />
            Yuklanmoqda...
          </div>
        </Card>
      ) : error ? (
        <Card>
          <div className="flex flex-col items-center justify-center h-64 gap-3">
            <div className="text-red-600 text-sm">{error}</div>
            <Button variant="outline" size="sm" onClick={() => window.location.reload()}>
              Qayta urinish
            </Button>
          </div>
        </Card>
      ) : (
        <Card>
          <div className="flex items-center gap-3 p-4 border-b border-zinc-100 flex-wrap">
            <Tabs
              value={statusFilter}
              onChange={setStatusFilter}
              items={[
                { value: 'all',       label: 'Barchasi',       count: counts.all },
                { value: 'completed', label: 'Muvaffaqiyatli', count: counts.completed },
                { value: 'failed',    label: 'Xato',           count: counts.failed },
                { value: 'pending',   label: 'Kutilmoqda',     count: counts.pending },
              ]}
            />
            <div className="flex-1" />
            <Select
              value={typeFilter}
              onChange={setTypeFilter}
              options={[
                { value: 'all', label: 'Tur: Barchasi' },
                ...fileTypes.map(t => ({ value: t, label: `Tur: ${t.toUpperCase()}` })),
              ]}
              className="w-44"
            />
          </div>

          {/* Breakdown table */}
          <Table>
            <THead>
              <tr>
                <th>Fayl turi</th>
                <th>Holat</th>
                <th className="text-right">Miqdori</th>
                <th className="text-right">O'rtacha vaqt</th>
                <th className="text-right">O'rtacha savollar</th>
                <th>Muvaffaqiyat foizi</th>
              </tr>
            </THead>
            <TBody>
              {filtered.map((b, i) => (
                <TR key={i}>
                  <td className="py-3">
                    <span className="uppercase font-mono text-xs bg-zinc-100 text-zinc-700 rounded px-2 py-1">
                      {b.file_type}
                    </span>
                  </td>
                  <td>
                    {b.status === 'completed' && <Badge tone="green" dot>muvaffaqiyatli</Badge>}
                    {b.status === 'failed' && <Badge tone="red" dot>xato</Badge>}
                    {b.status === 'pending' && (
                      <Badge tone="yellow"><IconLoader className="w-3 h-3 animate-spin" />kutilmoqda</Badge>
                    )}
                  </td>
                  <td className="text-right tnum text-sm font-medium">{(b.count || 0).toLocaleString()}</td>
                  <td className="text-right tnum text-sm text-zinc-600">{formatMs(b.avg_processing_ms)}</td>
                  <td className="text-right tnum text-sm text-zinc-600">
                    {b.avg_questions != null ? Math.round(b.avg_questions) : '—'}
                  </td>
                  <td>
                    {b.status === 'completed' ? (
                      <div className="flex items-center gap-2">
                        <div className="h-1.5 w-24 rounded-full bg-zinc-100 overflow-hidden">
                          <div className="h-full bg-emerald-500 w-full" />
                        </div>
                        <span className="text-xs text-emerald-600">100%</span>
                      </div>
                    ) : b.status === 'failed' ? (
                      <div className="flex items-center gap-2">
                        <div className="h-1.5 w-24 rounded-full bg-zinc-100 overflow-hidden">
                          <div className="h-full bg-red-400 w-full" />
                        </div>
                        <span className="text-xs text-red-600">0%</span>
                      </div>
                    ) : '—'}
                  </td>
                </TR>
              ))}
              {filtered.length === 0 && (
                <tr>
                  <td colSpan={6}>
                    <EmptyState
                      icon={IconFileImport}
                      title="Mos import topilmadi"
                      description="Boshqa holat yoki fayl turi filtrini sinab ko&#39;ring."
                    />
                  </td>
                </tr>
              )}
            </TBody>
          </Table>

          {/* Visual breakdown by file type */}
          {Object.keys(grouped).length > 0 && (
            <div className="border-t border-zinc-100 p-6">
              <div className="text-xs uppercase tracking-wider text-zinc-500 mb-4">Fayl turlari bo'yicha ko'rinish</div>
              <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
                {Object.entries(grouped).map(([ft, v]) => {
                  const total = v.ok + v.fail + v.pending;
                  const okPct = total > 0 ? (v.ok / total) * 100 : 0;
                  const failPct = total > 0 ? (v.fail / total) * 100 : 0;
                  const avgMs = v.msCount ? v.ms / v.msCount : 0;
                  const avgQ = v.avgQuestions.length > 0
                    ? v.avgQuestions.reduce((s, x) => s + x.val * x.cnt, 0) / v.avgQuestions.reduce((s, x) => s + x.cnt, 0)
                    : null;
                  return (
                    <div key={ft} className="rounded-lg border border-zinc-200 p-4">
                      <div className="flex items-center justify-between mb-3">
                        <div className="flex items-center gap-2">
                          <span className="uppercase font-mono text-xs bg-zinc-100 text-zinc-700 rounded px-1.5 py-0.5">{ft}</span>
                          <span className="text-sm font-medium text-zinc-900">{total} fayl</span>
                        </div>
                        <div className="text-xs text-zinc-500 tnum">~{formatMs(avgMs)}</div>
                      </div>
                      <div className="h-2 w-full rounded-full bg-zinc-100 overflow-hidden flex mb-2">
                        <div className="h-full bg-emerald-500 transition-all" style={{ width: `${okPct}%` }} />
                        <div className="h-full bg-red-400 transition-all" style={{ width: `${failPct}%` }} />
                      </div>
                      <div className="flex items-center gap-3 text-xs text-zinc-500">
                        <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-emerald-500" />{v.ok} ok</span>
                        {v.fail > 0 && <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-red-400" />{v.fail} xato</span>}
                        {v.pending > 0 && <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-amber-400" />{v.pending} kutilmoqda</span>}
                        {avgQ != null && <span className="ml-auto">~{Math.round(avgQ)} savol</span>}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </Card>
      )}
    </div>
  );
};

const MiniStat = ({ label, value, tone = 'neutral', loading = false }) => {
  const dots = { neutral: 'bg-zinc-400', green: 'bg-emerald-500', red: 'bg-red-500', yellow: 'bg-amber-500' };
  return (
    <Card>
      <CardContent className="pt-5 pb-5">
        <div className="flex items-center gap-2 text-xs text-zinc-500">
          <span className={cx('w-1.5 h-1.5 rounded-full', dots[tone])} /> {label}
        </div>
        {loading ? (
          <div className="text-2xl font-semibold tnum mt-2 text-zinc-300">—</div>
        ) : (
          <div className="text-2xl font-semibold tnum mt-2">{(value || 0).toLocaleString()}</div>
        )}
      </CardContent>
    </Card>
  );
};

Object.assign(window, { ImportLogsPage });
// Notifications page — Broadcast composer + History (mock history, real UI)

const MOCK_HISTORY = [
  {
    id: 7001,
    text: "Yangi yangilanish: AI import endi rasm fayllarini ham qo'llab-quvvatlaydi 🚀",
    language_code: 'uz',
    recipients: 1213,
    delivered: 1198,
    failed: 15,
    status: 'completed',
    created_at: new Date(Date.now() - 2 * 86400 * 1000).toISOString(),
    sent_by: 'admin',
  },
  {
    id: 7002,
    text: 'Праздничная акция: подписка на 30% дешевле до конца недели!',
    language_code: 'ru',
    recipients: 842,
    delivered: 831,
    failed: 11,
    status: 'completed',
    created_at: new Date(Date.now() - 5 * 86400 * 1000).toISOString(),
    sent_by: 'admin',
  },
  {
    id: 7003,
    text: 'New feature: leaderboards are now available for public quizzes.',
    language_code: 'en',
    recipients: 304,
    delivered: 301,
    failed: 3,
    status: 'completed',
    created_at: new Date(Date.now() - 9 * 86400 * 1000).toISOString(),
    sent_by: 'admin',
  },
  {
    id: 7004,
    text: 'Texnik ish: bugun 03:00 dan 04:00 gacha bot ishlamasligi mumkin.',
    language_code: 'all',
    recipients: 2350,
    delivered: 2301,
    failed: 49,
    status: 'completed',
    created_at: new Date(Date.now() - 14 * 86400 * 1000).toISOString(),
    sent_by: 'admin',
  },
];

const NotificationsPage = () => {
  const [tab, setTab] = React.useState('broadcast');
  const [history, setHistory] = React.useState(MOCK_HISTORY);

  const addToHistory = (item) => {
    setHistory(h => [item, ...h]);
  };

  return (
    <div className="p-8 max-w-[1400px] mx-auto">
      <PageHeader
        title="Xabarnomalar"
        description="Foydalanuvchilarga broadcast yuboring va o&#39;tgan yuborishlarni ko&#39;ring."
      />
      <div className="mb-5">
        <Tabs
          value={tab}
          onChange={setTab}
          items={[
            { value: 'broadcast', label: 'Broadcast' },
            { value: 'history',   label: 'Tarix', count: history.length },
          ]}
        />
      </div>
      {tab === 'broadcast' && <Broadcast onSent={addToHistory} />}
      {tab === 'history'   && <History notifications={history} />}
    </div>
  );
};

const Broadcast = ({ onSent }) => {
  const [text, setText] = React.useState('');
  const [language, setLanguage] = React.useState('all');
  const [audience, setAudience] = React.useState('all');
  const [parseMode, setParseMode] = React.useState('html');
  const [sending, setSending] = React.useState(false);
  const [confirm, setConfirm] = React.useState(false);
  const toast = useToast();

  const send = () => {
    setSending(true);
    // Simulate sending — no real broadcast API endpoint in spec
    setTimeout(() => {
      const item = {
        id: Date.now(),
        text,
        language_code: language,
        recipients: 0,
        delivered: 0,
        failed: 0,
        status: 'completed',
        created_at: new Date().toISOString(),
        sent_by: 'admin',
      };
      onSent(item);
      setSending(false);
      setConfirm(false);
      setText('');
      toast.success("Broadcast navbatga qo'yildi");
    }, 1200);
  };

  return (
    <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
      <Card className="xl:col-span-2">
        <CardHeader>
          <CardTitle>Broadcast yaratish</CardTitle>
          <CardDescription>Bu xabar sizning filtrlaringizga mos kelgan har bir foydalanuvchiga yuboriladi.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-5">
          <div>
            <Label>Xabar</Label>
            <Textarea
              placeholder="Salom {first_name}! Yangi narsa chiqardik — sinab ko&#39;ring 🎉"
              value={text}
              onChange={e => setText(e.target.value)}
              className="mt-1.5 min-h-[160px] font-mono text-[13px]"
              maxLength={4000}
            />
            <div className="flex items-center justify-between mt-1.5">
              <div className="text-xs text-zinc-500">
                O'zgaruvchilar: <code className="font-mono bg-zinc-100 px-1 rounded">{'{first_name}'}</code>, <code className="font-mono bg-zinc-100 px-1 rounded">{'{username}'}</code>
              </div>
              <div className="text-xs text-zinc-500 tnum">{text.length} / 4000</div>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label>Til</Label>
              <Select
                value={language}
                onChange={setLanguage}
                options={[
                  { value: 'all', label: 'Barcha tillar' },
                  { value: 'uz',  label: "O'zbek" },
                  { value: 'ru',  label: 'Русский' },
                  { value: 'en',  label: 'English' },
                ]}
                className="mt-1.5"
              />
            </div>
            <div>
              <Label>Auditoriya</Label>
              <Select
                value={audience}
                onChange={setAudience}
                options={[
                  { value: 'all',         label: 'Barcha foydalanuvchilar' },
                  { value: 'active',      label: 'Faollar (bloklanmaganlar)' },
                  { value: 'subscribers', label: 'Faqat obunachilар' },
                ]}
                className="mt-1.5"
              />
            </div>
          </div>

          <div>
            <Label>Parse mode</Label>
            <div className="mt-1.5 inline-flex rounded-md border border-zinc-200 overflow-hidden">
              {['plain', 'html', 'markdown'].map(m => (
                <button
                  key={m}
                  onClick={() => setParseMode(m)}
                  className={cx(
                    'px-3 h-9 text-sm capitalize',
                    parseMode === m ? 'bg-zinc-900 text-white' : 'bg-white text-zinc-700 hover:bg-zinc-50'
                  )}
                >
                  {m}
                </button>
              ))}
            </div>
          </div>
        </CardContent>
        <CardFooter className="justify-between">
          <div className="text-sm text-zinc-600">
            Broadcast tayyor
          </div>
          <div className="flex items-center gap-2">
            <Button variant="outline" disabled={!text.trim()}>Qoralama saqlash</Button>
            <Button onClick={() => setConfirm(true)} disabled={!text.trim()}>
              <IconSend className="w-4 h-4" />Broadcast yuborish
            </Button>
          </div>
        </CardFooter>
      </Card>

      {/* Preview */}
      <Card>
        <CardHeader>
          <CardTitle>Ko'rinish</CardTitle>
          <CardDescription>Foydalanuvchi chatida qanday ko'rinadi.</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="rounded-xl bg-zinc-100 border border-zinc-200 p-4">
            <div className="flex items-center gap-2 mb-3 text-xs text-zinc-500">
              <div className="w-8 h-8 rounded-full bg-zinc-900 text-white flex items-center justify-center text-sm font-bold">Q</div>
              <div>
                <div className="font-medium text-zinc-900">Quizly bot</div>
                <div className="text-[11px]">bot · online</div>
              </div>
            </div>
            <div className="bg-white rounded-2xl rounded-tl-md p-3 text-sm text-zinc-900 whitespace-pre-wrap shadow-card max-w-full break-words min-h-[48px]">
              {text || <span className="text-zinc-400">Xabaringiz shu yerda ko'rinadi…</span>}
            </div>
            <div className="text-[10px] text-zinc-400 mt-1 pl-1">@QuizlyBot orqali · {new Date().toLocaleTimeString('uz', { hour: '2-digit', minute: '2-digit' })}</div>
          </div>
          <div className="mt-4 text-xs text-zinc-500 space-y-1.5">
            <div className="flex items-center justify-between">
              <span>Parse mode</span>
              <span className="text-zinc-900 capitalize">{parseMode}</span>
            </div>
            <div className="flex items-center justify-between">
              <span>Til</span>
              <span className="text-zinc-900">{language === 'all' ? 'Barchasi' : language.toUpperCase()}</span>
            </div>
            <div className="flex items-center justify-between">
              <span>Auditoriya</span>
              <span className="text-zinc-900 capitalize">{audience}</span>
            </div>
          </div>
        </CardContent>
      </Card>

      <Dialog open={confirm} onClose={() => !sending && setConfirm(false)} maxW="max-w-md">
        <DialogHeader
          title="Bu broadcastni yuborish?"
          description="Bu amalni bekor qilib bo&#39;lmaydi."
          onClose={() => !sending && setConfirm(false)}
        />
        <DialogBody>
          <div className="rounded-lg border border-zinc-200 p-4 mb-3">
            <div className="text-xs uppercase tracking-wider text-zinc-500 mb-2">Xabar</div>
            <div className="text-sm text-zinc-900 whitespace-pre-wrap break-words max-h-32 overflow-y-auto">{text}</div>
          </div>
          <div className="text-sm text-zinc-700 space-y-1">
            {language !== 'all' && (
              <div>Til: <Badge tone="neutral" className="ml-1">{language}</Badge></div>
            )}
            <div>Auditoriya: <span className="font-medium">{audience}</span></div>
          </div>
        </DialogBody>
        <DialogFooter>
          <Button variant="outline" onClick={() => setConfirm(false)} disabled={sending}>Bekor</Button>
          <Button onClick={send} disabled={sending}>
            {sending ? <IconLoader className="w-4 h-4 animate-spin" /> : <IconSend className="w-4 h-4" />}
            {sending ? 'Yuborilmoqda…' : 'Hozir yuborish'}
          </Button>
        </DialogFooter>
      </Dialog>
    </div>
  );
};

const History = ({ notifications }) => {
  const [page, setPage] = React.useState(1);
  const limit = 10;
  const pages = Math.max(1, Math.ceil(notifications.length / limit));
  const slice = notifications.slice((page - 1) * limit, page * limit);

  return (
    <Card>
      <CardHeader>
        <CardTitle>O'tgan broadcastlar</CardTitle>
        <CardDescription>Eng yangi yuqorida.</CardDescription>
      </CardHeader>
      <CardContent className="px-0 pb-0">
        {notifications.length === 0 ? (
          <div className="flex items-center justify-center h-32 text-zinc-400 text-sm">
            Hali broadcast yuborilmagan
          </div>
        ) : (
          <ul className="divide-y divide-zinc-100">
            {slice.map(n => {
              const successRate = n.recipients > 0 ? (n.delivered / n.recipients) * 100 : 100;
              return (
                <li key={n.id} className="px-6 py-4 flex items-start gap-4">
                  <div className="w-9 h-9 rounded-full bg-zinc-100 flex items-center justify-center text-zinc-500 shrink-0">
                    <IconSend className="w-4 h-4" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1 flex-wrap">
                      {n.status === 'sending'
                        ? <Badge tone="yellow"><IconLoader className="w-3 h-3 animate-spin" />yuborilmoqda</Badge>
                        : <Badge tone="green" dot>tugallandi</Badge>}
                      {n.language_code && <Badge tone="neutral">{n.language_code}</Badge>}
                      {n.sent_by && <span className="text-xs text-zinc-500">by @{n.sent_by}</span>}
                      <span className="text-xs text-zinc-500 ml-auto tnum">{formatRelative(n.created_at)}</span>
                    </div>
                    <div className="text-sm text-zinc-900 line-clamp-2">{n.text}</div>
                    {n.recipients > 0 && (
                      <div className="mt-2 flex items-center gap-4 text-xs text-zinc-500 tnum">
                        <span><span className="text-zinc-900 font-medium">{n.recipients.toLocaleString()}</span> oluvchi</span>
                        <span><span className="text-emerald-600 font-medium">{n.delivered.toLocaleString()}</span> yetkazildi</span>
                        {n.failed > 0 && <span><span className="text-red-600 font-medium">{n.failed}</span> xato</span>}
                        <span className="ml-auto">{successRate.toFixed(1)}% muvaffaqiyat</span>
                      </div>
                    )}
                  </div>
                </li>
              );
            })}
          </ul>
        )}
        <Pagination page={page} pages={pages} total={notifications.length} limit={limit} onChange={setPage} />
      </CardContent>
    </Card>
  );
};

Object.assign(window, { NotificationsPage });
// Templates page — list of notification templates with inline edit

const TemplatesPage = () => {
  const templates = useStore(s => s.templates);
  const [expanded, setExpanded] = React.useState(null);
  const toast = useToast();

  const update = (slug, patch) => {
    store.set(s => ({
      ...s,
      templates: s.templates.map(t => t.slug === slug ? { ...t, ...patch } : t),
    }));
  };

  return (
    <div className="p-8 max-w-[1100px] mx-auto">
      <PageHeader
        title="Templates"
        description="Bot messages users receive at key moments. Edit text per language and toggle active state."
      />

      <div className="space-y-3">
        {templates.map(t => {
          const isOpen = expanded === t.slug;
          return (
            <Card key={t.slug}>
              <button
                onClick={() => setExpanded(isOpen ? null : t.slug)}
                className="w-full flex items-center gap-4 px-6 py-4 text-left"
              >
                <div className="w-9 h-9 rounded-md bg-zinc-100 flex items-center justify-center text-zinc-500 shrink-0">
                  <IconMessageSquare className="w-4 h-4" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-0.5">
                    <span className="text-sm font-semibold text-zinc-900">{t.name}</span>
                    <span className="text-xs font-mono text-zinc-500">{t.slug}</span>
                    {t.is_active
                      ? <Badge tone="green" dot>active</Badge>
                      : <Badge tone="neutral" dot>disabled</Badge>}
                  </div>
                  <div className="text-xs text-zinc-500">{t.description}</div>
                </div>
                <div onClick={e => e.stopPropagation()} className="shrink-0">
                  <Switch checked={t.is_active} onChange={(v) => { update(t.slug, { is_active: v }); toast.success(`${t.name} ${v ? 'enabled' : 'disabled'}`); }} />
                </div>
                <IconChevronDown className={cx('w-4 h-4 text-zinc-400 transition shrink-0', isOpen && 'rotate-180')} />
              </button>

              {isOpen && (
                <div className="border-t border-zinc-100 p-6 grid grid-cols-1 md:grid-cols-3 gap-4">
                  <TemplateField label="O‘zbek" code="uz" value={t.text_uz} onChange={v => update(t.slug, { text_uz: v })} />
                  <TemplateField label="Русский" code="ru" value={t.text_ru} onChange={v => update(t.slug, { text_ru: v })} />
                  <TemplateField label="English" code="en" value={t.text_en} onChange={v => update(t.slug, { text_en: v })} />
                  <div className="md:col-span-3 flex items-center justify-between">
                    <div className="text-xs text-zinc-500">Auto-saved. Variables: <code className="font-mono bg-zinc-100 px-1 rounded">{'{first_name}'}</code>, <code className="font-mono bg-zinc-100 px-1 rounded">{'{quiz_title}'}</code>, <code className="font-mono bg-zinc-100 px-1 rounded">{'{questions}'}</code>, <code className="font-mono bg-zinc-100 px-1 rounded">{'{days}'}</code></div>
                    <Button variant="outline" size="sm" onClick={() => toast.info('Sent test message to @farrukh_admin')}>
                      <IconSend className="w-3.5 h-3.5" />Send test
                    </Button>
                  </div>
                </div>
              )}
            </Card>
          );
        })}
      </div>
    </div>
  );
};

const TemplateField = ({ label, code, value, onChange }) => (
  <div>
    <div className="flex items-center gap-2 mb-1.5">
      <Label>{label}</Label>
      <Badge tone="neutral" className="font-mono">{code}</Badge>
    </div>
    <Textarea value={value} onChange={e => onChange(e.target.value)} className="min-h-[100px] font-mono text-[13px]" />
  </div>
);

Object.assign(window, { TemplatesPage });
// Settings page — real API for settings + admin management

const SettingsPage = () => {
  return (
    <div className="p-8 max-w-[1100px] mx-auto">
      <PageHeader
        title="Sozlamalar"
        description="Tizim konfiguratsiyasi va admin jamoasi."
      />
      <div className="space-y-6">
        <SystemSettings />
        <AdminManagement />
      </div>
    </div>
  );
};

const SystemSettings = () => {
  const [settings, setSettings] = React.useState({});
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState(null);
  const [editing, setEditing] = React.useState(null);
  const [draft, setDraft] = React.useState('');
  const [saving, setSaving] = React.useState(false);
  const toast = useToast();

  const loadSettings = () => {
    setLoading(true);
    setError(null);
    apiFetch('/settings')
      .then(data => {
        setSettings(data);
        setLoading(false);
      })
      .catch(err => {
        setError(err.message);
        setLoading(false);
      });
  };

  React.useEffect(() => { loadSettings(); }, []);

  const startEdit = (key, value) => {
    setEditing(key);
    setDraft(value);
  };

  const save = () => {
    setSaving(true);
    apiFetch(`/settings/${encodeURIComponent(editing)}`, {
      method: 'PUT',
      body: JSON.stringify({ value: draft }),
    })
      .then(() => {
        setSettings(s => ({
          ...s,
          [editing]: { ...s[editing], value: draft },
        }));
        toast.success(`${editing} saqlandi`);
        setEditing(null);
        setSaving(false);
      })
      .catch(err => {
        // Try to update locally even if API fails
        setSettings(s => ({
          ...s,
          [editing]: { ...s[editing], value: draft },
        }));
        toast.error(`Saqlashda xato: ${err.message}. Lokal yangilandi.`);
        setEditing(null);
        setSaving(false);
      });
  };

  const cancel = () => {
    setEditing(null);
    setDraft('');
  };

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle>Tizim konfiguratsiyasi</CardTitle>
            <CardDescription>Bot runtime tomonidan ishlatiladigan jonli qiymatlar.</CardDescription>
          </div>
          <Badge tone="neutral" className="font-mono"><IconBolt className="w-3 h-3" />jonli</Badge>
        </div>
      </CardHeader>
      <CardContent className="px-0 pb-0">
        {loading ? (
          <div className="flex items-center justify-center h-40 text-zinc-400 text-sm gap-2">
            <IconLoader className="w-5 h-5 animate-spin" />
            Yuklanmoqda...
          </div>
        ) : error ? (
          <div className="flex flex-col items-center justify-center h-40 gap-3">
            <div className="text-red-600 text-sm">{error}</div>
            <Button variant="outline" size="sm" onClick={loadSettings}>Qayta urinish</Button>
          </div>
        ) : Object.keys(settings).length === 0 ? (
          <div className="flex items-center justify-center h-40 text-zinc-400 text-sm">
            Sozlama topilmadi
          </div>
        ) : (
          <Table>
            <THead>
              <tr>
                <th>Kalit</th>
                <th>Qiymat</th>
                <th>Tavsif</th>
                <th className="text-right">Amallar</th>
              </tr>
            </THead>
            <TBody>
              {Object.entries(settings).map(([key, cfg]) => (
                <TR key={key}>
                  <td className="py-3 font-mono text-xs text-zinc-900">{key}</td>
                  <td>
                    {editing === key ? (
                      <div className="flex items-center gap-2">
                        <Input
                          value={draft}
                          onChange={e => setDraft(e.target.value)}
                          className="max-w-xs"
                          autoFocus
                          onKeyDown={e => { if (e.key === 'Enter') save(); if (e.key === 'Escape') cancel(); }}
                        />
                        <Button size="sm" onClick={save} disabled={saving}>
                          {saving ? <IconLoader className="w-3.5 h-3.5 animate-spin" /> : <IconCheck className="w-3.5 h-3.5" />}
                          Saqlash
                        </Button>
                        <Button size="sm" variant="ghost" onClick={cancel} disabled={saving}>Bekor</Button>
                      </div>
                    ) : (
                      <button
                        onClick={() => startEdit(key, cfg.value)}
                        className="font-mono text-sm text-zinc-900 bg-zinc-50 border border-zinc-200 rounded px-2 py-1 hover:bg-zinc-100 transition-colors"
                      >
                        {cfg.value}
                      </button>
                    )}
                  </td>
                  <td className="text-sm text-zinc-600 max-w-md">{cfg.description}</td>
                  <td className="text-right">
                    {editing !== key && (
                      <Button variant="ghost" size="sm" onClick={() => startEdit(key, cfg.value)}>
                        Tahrirlash
                      </Button>
                    )}
                  </td>
                </TR>
              ))}
            </TBody>
          </Table>
        )}
      </CardContent>
    </Card>
  );
};

const AdminManagement = () => {
  const [admins, setAdmins] = React.useState([]);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState(null);
  const [showAdd, setShowAdd] = React.useState(false);
  const [confirmRemove, setConfirmRemove] = React.useState(null);
  const [draft, setDraft] = React.useState({ telegram_id: '', username: '', role: 'admin' });
  const [submitting, setSubmitting] = React.useState(false);
  const [removing, setRemoving] = React.useState(false);
  const toast = useToast();

  const loadAdmins = () => {
    setLoading(true);
    setError(null);
    apiFetch('/admins')
      .then(data => {
        setAdmins(data.admins || data || []);
        setLoading(false);
      })
      .catch(err => {
        setError(err.message);
        setLoading(false);
      });
  };

  React.useEffect(() => { loadAdmins(); }, []);

  const submit = () => {
    if (!draft.telegram_id || !draft.username) {
      toast.error("Iltimos, ikkala maydonni ham to'ldiring");
      return;
    }
    setSubmitting(true);
    apiFetch('/admins', {
      method: 'POST',
      body: JSON.stringify({
        telegram_id: parseInt(draft.telegram_id, 10),
        username: draft.username.replace(/^@/, ''),
        role: draft.role,
      }),
    })
      .then(newAdmin => {
        setAdmins(a => [...a, newAdmin]);
        toast.success(`@${newAdmin.username || draft.username} qo'shildi`);
        setShowAdd(false);
        setDraft({ telegram_id: '', username: '', role: 'admin' });
        setSubmitting(false);
      })
      .catch(err => {
        toast.error(`Qo'shishda xato: ${err.message}`);
        setSubmitting(false);
      });
  };

  const remove = (a) => {
    setRemoving(true);
    apiFetch(`/admins/${a.id}`, { method: 'DELETE' })
      .then(() => {
        setAdmins(list => list.filter(x => x.id !== a.id));
        toast.success(`@${a.username} o'chirildi`);
        setConfirmRemove(null);
        setRemoving(false);
      })
      .catch(err => {
        toast.error(`O'chirishda xato: ${err.message}`);
        setRemoving(false);
      });
  };

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle>Admin jamoasi</CardTitle>
            <CardDescription>Bu dashboardga kirish huquqiga ega odamlar.</CardDescription>
          </div>
          <Button onClick={() => setShowAdd(true)}>
            <IconPlus className="w-4 h-4" />Admin qo'shish
          </Button>
        </div>
      </CardHeader>
      <CardContent className="px-0 pb-0">
        {loading ? (
          <div className="flex items-center justify-center h-32 text-zinc-400 text-sm gap-2">
            <IconLoader className="w-5 h-5 animate-spin" />
            Yuklanmoqda...
          </div>
        ) : error ? (
          <div className="flex flex-col items-center justify-center h-32 gap-3">
            <div className="text-red-600 text-sm">{error}</div>
            <Button variant="outline" size="sm" onClick={loadAdmins}>Qayta urinish</Button>
          </div>
        ) : (
          <Table>
            <THead>
              <tr>
                <th>Admin</th>
                <th>Telegram ID</th>
                <th>Rol</th>
                <th>Qo'shilgan</th>
                <th className="text-right">Amallar</th>
              </tr>
            </THead>
            <TBody>
              {admins.map(a => (
                <TR key={a.id}>
                  <td className="py-3">
                    <div className="flex items-center gap-3">
                      <Avatar name={a.username || 'Admin'} size="md" />
                      <div>
                        <div className="text-sm font-medium text-zinc-900">@{a.username}</div>
                        <div className="text-xs text-zinc-500 font-mono">id {a.id}</div>
                      </div>
                    </div>
                  </td>
                  <td className="font-mono text-xs text-zinc-600 tnum">{a.telegram_id}</td>
                  <td>
                    {a.role === 'owner'   && <Badge tone="violet" dot>owner</Badge>}
                    {a.role === 'admin'   && <Badge tone="blue" dot>admin</Badge>}
                    {a.role === 'support' && <Badge tone="neutral" dot>support</Badge>}
                    {!['owner','admin','support'].includes(a.role) && <Badge tone="neutral" dot>{a.role}</Badge>}
                  </td>
                  <td className="text-sm text-zinc-600 tnum">
                    {a.created_at ? formatDate(a.created_at) : '—'}
                  </td>
                  <td className="text-right">
                    {a.role === 'owner' ? (
                      <span className="text-xs text-zinc-400">o'chirish mumkin emas</span>
                    ) : (
                      <Button variant="ghost" size="sm" onClick={() => setConfirmRemove(a)}>
                        <IconTrash className="w-3.5 h-3.5 text-red-600" />O'chirish
                      </Button>
                    )}
                  </td>
                </TR>
              ))}
              {admins.length === 0 && (
                <tr>
                  <td colSpan={5}>
                    <EmptyState icon={IconUsers} title="Admin topilmadi" description="" />
                  </td>
                </tr>
              )}
            </TBody>
          </Table>
        )}
      </CardContent>

      {/* Add admin dialog */}
      <Dialog open={showAdd} onClose={() => !submitting && setShowAdd(false)} maxW="max-w-md">
        <DialogHeader
          title="Admin qo&#39;shish"
          description="U keyingi kirganida bu dashboardni ko&#39;radi."
          onClose={() => !submitting && setShowAdd(false)}
        />
        <DialogBody className="space-y-4">
          <div>
            <Label>Telegram ID</Label>
            <Input
              className="mt-1.5"
              placeholder="312445001"
              value={draft.telegram_id}
              onChange={e => setDraft({ ...draft, telegram_id: e.target.value.replace(/\D/g, '') })}
            />
          </div>
          <div>
            <Label>Username</Label>
            <Input
              className="mt-1.5"
              placeholder="@username"
              value={draft.username}
              onChange={e => setDraft({ ...draft, username: e.target.value })}
            />
          </div>
          <div>
            <Label>Rol</Label>
            <Select
              value={draft.role}
              onChange={v => setDraft({ ...draft, role: v })}
              options={[
                { value: 'admin',   label: "Admin · to'liq kirish" },
                { value: 'support', label: 'Support · foydalanuvchilar va xabarlar' },
              ]}
              className="mt-1.5"
            />
          </div>
        </DialogBody>
        <DialogFooter>
          <Button variant="outline" onClick={() => setShowAdd(false)} disabled={submitting}>Bekor</Button>
          <Button onClick={submit} disabled={submitting}>
            {submitting ? <IconLoader className="w-4 h-4 animate-spin" /> : <IconPlus className="w-4 h-4" />}
            Admin qo'shish
          </Button>
        </DialogFooter>
      </Dialog>

      {/* Remove confirm dialog */}
      <Dialog open={!!confirmRemove} onClose={() => !removing && setConfirmRemove(null)} maxW="max-w-md">
        <DialogHeader
          title="Bu adminni o&#39;chirish?"
          description="U darhol kirishdan mahrum bo&#39;ladi."
          onClose={() => !removing && setConfirmRemove(null)}
        />
        <DialogBody>
          {confirmRemove && (
            <div className="rounded-lg border border-zinc-200 p-4 flex items-center gap-3">
              <Avatar name={confirmRemove.username || 'Admin'} size="md" />
              <div>
                <div className="text-sm font-medium">@{confirmRemove.username}</div>
                <div className="text-xs text-zinc-500 font-mono">{confirmRemove.telegram_id} · {confirmRemove.role}</div>
              </div>
            </div>
          )}
        </DialogBody>
        <DialogFooter>
          <Button variant="outline" onClick={() => setConfirmRemove(null)} disabled={removing}>Bekor</Button>
          <Button variant="destructive" onClick={() => remove(confirmRemove)} disabled={removing}>
            {removing ? <IconLoader className="w-4 h-4 animate-spin" /> : <IconTrash className="w-4 h-4" />}
            O'chirish
          </Button>
        </DialogFooter>
      </Dialog>
    </Card>
  );
};

Object.assign(window, { SettingsPage });
// Main app — auth state + hash routing + layout + tweaks panel

const useHashRoute = () => {
  const get = () => (window.location.hash || '#/').slice(1) || '/';
  const [path, setPath] = React.useState(get());
  React.useEffect(() => {
    const onHash = () => setPath(get());
    window.addEventListener('hashchange', onHash);
    return () => window.removeEventListener('hashchange', onHash);
  }, []);
  const navigate = React.useCallback((p) => { window.location.hash = '#' + p; }, []);
  return [path, navigate];
};

const TWEAK_DEFAULTS = /*EDITMODE-BEGIN*/{
  "sidebar": "dark",
  "density": "comfortable",
  "showSpeakerTip": true
}/*EDITMODE-END*/;

const QuizlyAdminApp = () => {
  const [auth, setAuth] = React.useState(() => {
    try { return !!localStorage.getItem('admin_token'); } catch { return false; }
  });
  const [path, navigate] = useHashRoute();
  const [cmdOpen, setCmdOpen] = React.useState(false);
  const [tweaks, setTweak] = useTweaks(TWEAK_DEFAULTS);

  // Keyboard shortcut for command palette
  React.useEffect(() => {
    const onKey = (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        setCmdOpen(true);
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);

  const onLogin = (token, remember) => {
    if (remember) {
      try { localStorage.setItem('admin_token', token); } catch {}
    }
    setAuth(true);
    navigate('/');
    // Real API dan ma'lumot yuklash
    setTimeout(() => loadRealData(), 100);
  };

  // Sahifa ochilganda token mavjud bo'lsa — yuklash
  React.useEffect(() => {
    if (auth) loadRealData();
  }, [auth]);
  const onLogout = () => {
    try { localStorage.removeItem('admin_token'); } catch {}
    setAuth(false);
    store.set(s => ({ ...s, _loaded: false, _loading: false }));
  };

  if (!auth) {
    return (
      <ToastProvider>
        <LoginPage onLogin={onLogin} />
      </ToastProvider>
    );
  }

  let Page;
  if (path === '/' || path === '') Page = DashboardPage;
  else if (path.startsWith('/users')) Page = UsersPage;
  else if (path.startsWith('/quizzes')) Page = QuizzesPage;
  else if (path.startsWith('/import-logs')) Page = ImportLogsPage;
  else if (path.startsWith('/notifications')) Page = NotificationsPage;
  else if (path.startsWith('/templates')) Page = TemplatesPage;
  else if (path.startsWith('/settings')) Page = SettingsPage;
  else Page = DashboardPage;

  return (
    <ToastProvider>
      <div className={cx('flex h-full min-h-screen', tweaks.density === 'tight' && 'text-[13px]')}>
        <Sidebar path={path} onNavigate={navigate} onLogout={onLogout} tweaks={tweaks} />
        <div className="flex-1 min-w-0 flex flex-col">
          <Topbar path={path} onOpenCmd={() => setCmdOpen(true)} />
          <main className={cx('flex-1 overflow-y-auto bg-zinc-50', tweaks.density === 'tight' && '[&_.p-8]:p-6')}>
            <Page />
          </main>
        </div>
        <CommandPalette open={cmdOpen} onClose={() => setCmdOpen(false)} onNavigate={navigate} />
      </div>

      <TweaksPanel title="Tweaks">
        <TweakSection label="Layout">
          <TweakRadio
            label="Sidebar"
            value={tweaks.sidebar}
            onChange={(v) => setTweak('sidebar', v)}
            options={[
              { value: 'dark',  label: 'Dark' },
              { value: 'light', label: 'Light' },
            ]}
          />
          <TweakRadio
            label="Density"
            value={tweaks.density}
            onChange={(v) => setTweak('density', v)}
            options={[
              { value: 'comfortable', label: 'Comfortable' },
              { value: 'tight',       label: 'Tight' },
            ]}
          />
        </TweakSection>
        <TweakSection label="Demo">
          <TweakButton label="Simulate +1 signup" onClick={() => {
            store.set(s => ({
              ...s,
              overview: { ...s.overview,
                users: { ...s.overview.users, total: s.overview.users.total + 1, new_today: s.overview.users.new_today + 1 } },
            }));
          }} />
          <TweakButton label="Simulate +49,000 UZS payment" onClick={() => {
            store.set(s => ({
              ...s,
              overview: { ...s.overview,
                revenue: { ...s.overview.revenue,
                  total_uzs: s.overview.revenue.total_uzs + 49000,
                  this_month_uzs: s.overview.revenue.this_month_uzs + 49000 } },
            }));
          }} />
          <TweakButton label="Sign out (back to login)" onClick={onLogout} secondary />
        </TweakSection>
      </TweaksPanel>
    </ToastProvider>
  );
};

ReactDOM.createRoot(document.getElementById('root')).render(<QuizlyAdminApp />);
