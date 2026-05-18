// Import logs page

const ImportLogsPage = () => {
  const logs = useStore(s => s.importLogs);
  const breakdown = useStore(s => s.importBreakdown);
  const [page, setPage] = React.useState(1);
  const [limit] = React.useState(10);
  const [status, setStatus] = React.useState('all');
  const [type, setType] = React.useState('all');

  const filtered = React.useMemo(() => logs.filter(l =>
    (status === 'all' || l.status === status) &&
    (type === 'all' || l.file_type === type)
  ), [logs, status, type]);
  const total = filtered.length;
  const pages = Math.max(1, Math.ceil(total / limit));
  const slice = filtered.slice((page - 1) * limit, page * limit);
  React.useEffect(() => { setPage(1); }, [status, type]);

  const counts = {
    all:       logs.length,
    completed: logs.filter(l => l.status === 'completed').length,
    failed:    logs.filter(l => l.status === 'failed').length,
    pending:   logs.filter(l => l.status === 'pending').length,
  };

  return (
    <div className="p-8 max-w-[1400px] mx-auto">
      <PageHeader
        title="Import logs"
        description="History of AI file processing jobs (PDF, DOCX, image)."
      />

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <MiniStat label="Total runs" value={counts.all} tone="neutral" />
        <MiniStat label="Completed" value={counts.completed} tone="green" />
        <MiniStat label="Failed" value={counts.failed} tone="red" />
        <MiniStat label="Pending" value={counts.pending} tone="yellow" />
      </div>

      <Card>
        <div className="flex items-center gap-3 p-4 border-b border-zinc-100">
          <Tabs
            value={status}
            onChange={setStatus}
            items={[
              { value: 'all',       label: 'All',       count: counts.all },
              { value: 'completed', label: 'Completed', count: counts.completed },
              { value: 'failed',    label: 'Failed',    count: counts.failed },
              { value: 'pending',   label: 'Pending',   count: counts.pending },
            ]}
          />
          <div className="flex-1" />
          <Select
            value={type}
            onChange={setType}
            options={[
              { value: 'all',   label: 'Type: All' },
              { value: 'pdf',   label: 'Type: PDF' },
              { value: 'docx',  label: 'Type: DOCX' },
              { value: 'image', label: 'Type: Image' },
              { value: 'txt',   label: 'Type: TXT' },
            ]}
            className="w-40"
          />
        </div>

        <Table>
          <THead>
            <tr>
              <th>File</th>
              <th>Status</th>
              <th className="text-right">Imported</th>
              <th className="text-right">Processing</th>
              <th>User</th>
              <th>Created</th>
            </tr>
          </THead>
          <TBody>
            {slice.map(l => (
              <TR key={l.id}>
                <td className="py-3">
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-md bg-zinc-100 flex items-center justify-center text-zinc-500">
                      <IconFile className="w-4 h-4" />
                    </div>
                    <div className="min-w-0">
                      <div className="text-sm font-medium text-zinc-900 truncate font-mono">{l.file_name}</div>
                      <div className="text-xs text-zinc-500 uppercase">{l.file_type}</div>
                    </div>
                  </div>
                </td>
                <td>
                  {l.status === 'completed' && <Badge tone="green" dot>completed</Badge>}
                  {l.status === 'failed' && (
                    <div className="space-y-1">
                      <Badge tone="red" dot>failed</Badge>
                      {l.error && <div className="text-xs text-red-600 max-w-[200px] truncate">{l.error}</div>}
                    </div>
                  )}
                  {l.status === 'pending' && (
                    <Badge tone="yellow"><IconLoader className="w-3 h-3 animate-spin" />processing</Badge>
                  )}
                </td>
                <td className="text-right tnum text-sm">{l.total_imported || '—'}</td>
                <td className="text-right tnum text-sm text-zinc-600">{formatMs(l.processing_time_ms)}</td>
                <td className="text-sm text-zinc-600 font-mono">id{l.user_id}</td>
                <td className="text-sm text-zinc-600 tnum">{formatRelative(l.created_at)}</td>
              </TR>
            ))}
            {slice.length === 0 && (
              <tr><td colSpan={6}><EmptyState icon={IconFileImport} title="No matching imports" description="Try a different status or file-type filter." /></td></tr>
            )}
          </TBody>
        </Table>

        <Pagination page={page} pages={pages} total={total} limit={limit} onChange={setPage} />
      </Card>
    </div>
  );
};

const MiniStat = ({ label, value, tone = 'neutral' }) => {
  const dots = { neutral: 'bg-zinc-400', green: 'bg-emerald-500', red: 'bg-red-500', yellow: 'bg-amber-500' };
  return (
    <Card>
      <CardContent className="pt-5 pb-5">
        <div className="flex items-center gap-2 text-xs text-zinc-500">
          <span className={cx('w-1.5 h-1.5 rounded-full', dots[tone])} /> {label}
        </div>
        <div className="text-2xl font-semibold tnum mt-2">{value.toLocaleString()}</div>
      </CardContent>
    </Card>
  );
};

Object.assign(window, { ImportLogsPage });
