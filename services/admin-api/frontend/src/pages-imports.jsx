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
