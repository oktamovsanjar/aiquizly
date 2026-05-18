// Dashboard — overview cards + charts

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
        {spark && <Sparkline data={spark} color={color} width={84} height={28} />}
      </div>
    </CardContent>
  </Card>
);

const DashboardPage = () => {
  const overview = useStore(s => s.overview);
  const growth = useStore(s => s.growth30);
  const revenue = useStore(s => s.revenue30);
  const [range, setRange] = React.useState('30');

  const days = parseInt(range, 10);
  const growthSlice = growth.slice(-days);
  const revSlice = revenue.slice(-days);

  const totalRev = revSlice.reduce((a, b) => a + b.amount_uzs, 0);
  const totalCount = revSlice.reduce((a, b) => a + b.count, 0);

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
          <Button variant="outline" size="md">
            <IconCalendar className="w-4 h-4" />
            May 18, 2026
          </Button>
        </div>
      </PageHeader>

      {/* Stat row */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4 mb-6">
        <StatCard
          icon={IconUsers}
          label="Total users"
          value={overview.users.total.toLocaleString()}
          sub={<><span className="text-emerald-600 font-medium">+{overview.users.new_today}</span> today · {overview.users.active_this_week.toLocaleString()} active this week</>}
          trend={8.2}
          spark={growthSlice.map(g => g.new_users)}
          color="rgb(24 24 27)"
        />
        <StatCard
          icon={IconBookOpen}
          label="Total quizzes"
          value={overview.quizzes.total.toLocaleString()}
          sub={<>{overview.quizzes.public.toLocaleString()} public · {overview.quizzes.private.toLocaleString()} private</>}
          trend={5.4}
          spark={growthSlice.map(g => g.new_quizzes)}
          color="rgb(59 130 246)"
        />
        <StatCard
          icon={IconActivity}
          label="Active subscriptions"
          value={overview.subscriptions.active.toLocaleString()}
          sub={<>{((overview.subscriptions.active / overview.users.total) * 100).toFixed(1)}% conversion</>}
          trend={2.1}
          spark={[12, 14, 13, 15, 18, 17, 19, 22, 21, 24, 23, 26]}
          color="rgb(16 185 129)"
        />
        <StatCard
          icon={IconWallet}
          label="Revenue (this month)"
          value={formatUZS(overview.revenue.this_month_uzs)}
          sub={<>Lifetime {formatUZS(overview.revenue.total_uzs)}</>}
          trend={-1.4}
          spark={revSlice.map(r => r.amount_uzs)}
          color="rgb(245 158 11)"
        />
      </div>

      {/* Charts row */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-4 mb-6">
        <Card className="xl:col-span-2">
          <CardHeader>
            <div className="flex items-start justify-between">
              <div>
                <CardTitle>Growth</CardTitle>
                <CardDescription>New users and quizzes per day</CardDescription>
              </div>
              <div className="text-right">
                <div className="text-2xl font-semibold tnum">{growthSlice.reduce((a, g) => a + g.new_users, 0)}</div>
                <div className="text-xs text-zinc-500">new users · {days}d</div>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <LineChart
              data={growthSlice}
              height={260}
              series={[
                { key: 'new_users',   label: 'Users',   color: 'rgb(24 24 27)' },
                { key: 'new_quizzes', label: 'Quizzes', color: 'rgb(59 130 246)' },
              ]}
            />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <div className="flex items-start justify-between">
              <div>
                <CardTitle>Revenue</CardTitle>
                <CardDescription>UZS · last {days} days</CardDescription>
              </div>
              <div className="text-right">
                <div className="text-2xl font-semibold tnum">{formatUZS(totalRev)}</div>
                <div className="text-xs text-zinc-500">{totalCount} payments</div>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <BarChart
              data={revSlice}
              height={260}
              valueKey="amount_uzs"
              color="rgb(24 24 27)"
              yFormatter={(n) => n >= 1_000_000 ? `${(n / 1_000_000).toFixed(1)}M` : n >= 1000 ? `${(n / 1000).toFixed(0)}K` : n.toString()}
              tooltipFormatter={(d) => `${formatUZS(d.amount_uzs)} · ${d.count} payments`}
            />
          </CardContent>
        </Card>
      </div>

      {/* Lower row — recent activity + import health */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">
        <Card className="xl:col-span-2">
          <CardHeader>
            <CardTitle>Recent activity</CardTitle>
            <CardDescription>What happened in the last 24 hours</CardDescription>
          </CardHeader>
          <CardContent className="px-0 pb-0">
            <ul className="divide-y divide-zinc-100">
              {[
                { icon: IconUsers, color: 'bg-emerald-100 text-emerald-700', text: <><b>Aziza K.</b> subscribed to <b>yearly</b> plan</>, time: '12 min ago', amount: '+449,000 UZS' },
                { icon: IconFileImport, color: 'bg-blue-100 text-blue-700', text: <>AI import completed — <b>Tarix_imtihoni.pdf</b> · 26 questions</>, time: '38 min ago' },
                { icon: IconSend, color: 'bg-violet-100 text-violet-700', text: <>Broadcast <b>"AI import endi rasm fayllarini…"</b> sent to <b>1,213</b> users</>, time: '1 h ago' },
                { icon: IconBan, color: 'bg-red-100 text-red-700', text: <><b>id518040219</b> blocked by <b>aziza_pm</b></>, time: '2 h ago' },
                { icon: IconBookOpen, color: 'bg-amber-100 text-amber-800', text: <><b>Rustam Y.</b> made <b>"World Capitals Mega Pack"</b> public</>, time: '3 h ago' },
                { icon: IconWallet, color: 'bg-emerald-100 text-emerald-700', text: <>Payment received via <b>Payme</b></>, time: '4 h ago', amount: '+129,000 UZS' },
              ].map((row, i) => {
                const I = row.icon;
                return (
                  <li key={i} className="flex items-center gap-3 px-6 py-3">
                    <div className={cx('w-8 h-8 rounded-full flex items-center justify-center shrink-0', row.color)}>
                      <I className="w-4 h-4" />
                    </div>
                    <div className="flex-1 text-sm text-zinc-700">{row.text}</div>
                    {row.amount && <div className="text-sm tnum font-medium text-zinc-900">{row.amount}</div>}
                    <div className="text-xs text-zinc-500 tnum w-20 text-right">{row.time}</div>
                  </li>
                );
              })}
            </ul>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>AI imports — health</CardTitle>
            <CardDescription>By file type, last 30 days</CardDescription>
          </CardHeader>
          <CardContent className="px-0 pb-0">
            <ul className="divide-y divide-zinc-100">
              {(() => {
                const breakdown = store.get().importBreakdown;
                // group by file_type
                const grouped = {};
                breakdown.forEach(b => {
                  if (!grouped[b.file_type]) grouped[b.file_type] = { ok: 0, fail: 0, pending: 0, ms: 0, msCount: 0 };
                  grouped[b.file_type][b.status === 'completed' ? 'ok' : b.status === 'failed' ? 'fail' : 'pending'] += b.count;
                  if (b.avg_processing_ms) { grouped[b.file_type].ms += b.avg_processing_ms * b.count; grouped[b.file_type].msCount += b.count; }
                });
                return Object.entries(grouped).map(([ft, v]) => {
                  const total = v.ok + v.fail + v.pending;
                  const okPct = (v.ok / total) * 100;
                  const failPct = (v.fail / total) * 100;
                  const avgMs = v.msCount ? v.ms / v.msCount : 0;
                  return (
                    <li key={ft} className="px-6 py-4">
                      <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center gap-2">
                          <span className="uppercase font-mono text-xs bg-zinc-100 text-zinc-700 rounded px-1.5 py-0.5">{ft}</span>
                          <span className="text-sm text-zinc-900 font-medium">{total} files</span>
                        </div>
                        <div className="text-xs text-zinc-500 tnum">avg {formatMs(avgMs)}</div>
                      </div>
                      <div className="h-1.5 w-full rounded-full bg-zinc-100 overflow-hidden flex">
                        <div className="h-full bg-emerald-500" style={{ width: `${okPct}%` }} />
                        <div className="h-full bg-red-400" style={{ width: `${failPct}%` }} />
                      </div>
                      <div className="flex items-center gap-3 mt-2 text-xs text-zinc-500">
                        <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-emerald-500" /> {v.ok} ok</span>
                        {v.fail > 0 && <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-red-400" /> {v.fail} failed</span>}
                        {v.pending > 0 && <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-amber-400" /> {v.pending} pending</span>}
                      </div>
                    </li>
                  );
                });
              })()}
            </ul>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

Object.assign(window, { DashboardPage });
