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
          <div className="text-red-600 text-sm">{error || 'Ma\'lumot yuklanmadi'}</div>
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
