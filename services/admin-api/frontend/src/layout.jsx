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
