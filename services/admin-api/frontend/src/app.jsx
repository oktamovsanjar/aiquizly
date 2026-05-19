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
