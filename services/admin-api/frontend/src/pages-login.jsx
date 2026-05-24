// Login page — token input + remember + demo helper.

const LoginPage = ({ onLogin }) => {
  const [token, setToken] = React.useState('');
  const [show, setShow] = React.useState(false);
  const [remember, setRemember] = React.useState(true);
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState('');

  const submit = async (e) => {
    e.preventDefault();
    setError('');
    if (token.trim().length < 6) {
      setError('Token looks too short. Paste the full admin token.');
      return;
    }
    setLoading(true);
    try {
      const origin = window.location.origin;
      const prefix = window.location.pathname.startsWith('/admin') ? '/admin' : '';
      const res = await fetch(origin + prefix + '/analytics/overview', {
        headers: { 'X-Admin-Token': token.trim(), 'Content-Type': 'application/json' },
      });
      if (res.status === 403) {
        setError('Token noto\'g\'ri. Iltimos, to\'g\'ri admin tokenni kiriting.');
        setLoading(false);
        return;
      }
      if (!res.ok && res.status !== 200) {
        setError('Server xatosi. Qayta urinib ko\'ring.');
        setLoading(false);
        return;
      }
      onLogin(token.trim(), remember);
    } catch {
      setError('Serverga ulanib bo\'lmadi. Qayta urinib ko\'ring.');
    } finally {
      setLoading(false);
    }
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
