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
