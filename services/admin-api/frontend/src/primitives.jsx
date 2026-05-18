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
