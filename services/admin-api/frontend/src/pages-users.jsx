// Users page — searchable paginated table + detail modal

const UsersPage = () => {
  const users = useStore(s => s.users);
  const [page, setPage] = React.useState(1);
  const [limit] = React.useState(10);
  const [search, setSearch] = React.useState('');
  const [filter, setFilter] = React.useState('all'); // all | active | blocked
  const [selected, setSelected] = React.useState(null);
  const toast = useToast();

  const filtered = React.useMemo(() => {
    return users.filter(u => {
      if (filter === 'blocked' && !u.is_blocked) return false;
      if (filter === 'active' && u.is_blocked) return false;
      if (!search) return true;
      const q = search.toLowerCase();
      return (
        (u.username || '').toLowerCase().includes(q) ||
        (u.first_name || '').toLowerCase().includes(q) ||
        (u.last_name || '').toLowerCase().includes(q) ||
        String(u.telegram_id).includes(q)
      );
    });
  }, [users, search, filter]);

  const total = filtered.length;
  const pages = Math.max(1, Math.ceil(total / limit));
  const slice = filtered.slice((page - 1) * limit, page * limit);

  React.useEffect(() => { setPage(1); }, [search, filter]);

  const toggleBlock = (u) => {
    store.set(s => ({
      ...s,
      users: s.users.map(x => x.id === u.id ? { ...x, is_blocked: !x.is_blocked } : x),
    }));
    toast.success(u.is_blocked ? `Unblocked ${u.first_name}` : `Blocked ${u.first_name}`);
    if (selected && selected.id === u.id) setSelected({ ...u, is_blocked: !u.is_blocked });
  };

  return (
    <div className="p-8 max-w-[1400px] mx-auto">
      <PageHeader
        title="Users"
        description={<>Manage all <span className="tnum">{users.length.toLocaleString()}</span> Quizly users.</>}
      >
        <Button variant="outline"><IconArrowUpRight className="w-4 h-4" />Export CSV</Button>
      </PageHeader>

      <Card>
        <div className="flex items-center gap-3 p-4 border-b border-zinc-100">
          <Input
            placeholder="Search by name, username or telegram id…"
            value={search}
            onChange={e => setSearch(e.target.value)}
            leftIcon={<IconSearch className="w-4 h-4" />}
            className="max-w-sm"
          />
          <Tabs
            value={filter}
            onChange={setFilter}
            items={[
              { value: 'all',     label: 'All',     count: users.length },
              { value: 'active',  label: 'Active',  count: users.filter(u => !u.is_blocked).length },
              { value: 'blocked', label: 'Blocked', count: users.filter(u => u.is_blocked).length },
            ]}
          />
          <div className="flex-1" />
          <Select
            value="recent"
            onChange={() => {}}
            options={[
              { value: 'recent', label: 'Sort: last active' },
              { value: 'new',    label: 'Sort: newest' },
              { value: 'paid',   label: 'Sort: most paid' },
            ]}
            className="w-44"
          />
        </div>

        <Table>
          <THead>
            <tr>
              <th>User</th>
              <th>Telegram ID</th>
              <th>Lang</th>
              <th>Quizzes</th>
              <th>Last active</th>
              <th>Status</th>
              <th className="text-right">Actions</th>
            </tr>
          </THead>
          <TBody>
            {slice.map((u) => (
              <TR
                key={u.id}
                onClick={() => setSelected(u)}
                className="cursor-pointer"
              >
                <td className="py-3">
                  <div className="flex items-center gap-3">
                    <Avatar name={`${u.first_name} ${u.last_name || ''}`} size="md" />
                    <div className="min-w-0">
                      <div className="text-sm font-medium text-zinc-900 truncate">
                        {u.first_name} {u.last_name || ''}
                      </div>
                      <div className="text-xs text-zinc-500 truncate">
                        {u.username ? `@${u.username}` : <span className="italic">no username</span>}
                      </div>
                    </div>
                  </div>
                </td>
                <td className="font-mono text-xs text-zinc-600 tnum">{u.telegram_id}</td>
                <td><Badge tone="neutral">{u.language_code}</Badge></td>
                <td className="tnum text-sm">{u.quiz_count}</td>
                <td className="text-sm text-zinc-600 tnum">{formatRelative(u.last_active_at)}</td>
                <td>
                  {u.is_blocked
                    ? <Badge tone="red" dot>blocked</Badge>
                    : u.subscription
                      ? <Badge tone="green" dot>{u.subscription.plan}</Badge>
                      : <Badge tone="neutral" dot>free</Badge>}
                </td>
                <td className="text-right" onClick={e => e.stopPropagation()}>
                  <Button
                    variant={u.is_blocked ? 'outline' : 'ghost'}
                    size="sm"
                    onClick={() => toggleBlock(u)}
                  >
                    {u.is_blocked ? <><IconRotate className="w-3.5 h-3.5" />Unblock</> : <><IconBan className="w-3.5 h-3.5" />Block</>}
                  </Button>
                </td>
              </TR>
            ))}
            {slice.length === 0 && (
              <tr><td colSpan={7}><EmptyState icon={IconUsers} title="No users match your filter" description="Try clearing the search or changing the status filter." /></td></tr>
            )}
          </TBody>
        </Table>

        <Pagination page={page} pages={pages} total={total} limit={limit} onChange={setPage} />
      </Card>

      <UserDetailDialog user={selected} onClose={() => setSelected(null)} onToggleBlock={toggleBlock} />
    </div>
  );
};

const UserDetailDialog = ({ user, onClose, onToggleBlock }) => {
  if (!user) return null;
  const name = `${user.first_name} ${user.last_name || ''}`.trim();
  return (
    <Dialog open={!!user} onClose={onClose} maxW="max-w-2xl">
      <DialogHeader
        title={<div className="flex items-center gap-3"><Avatar name={name} size="lg" /><div><div className="text-base font-semibold">{name}</div><div className="text-xs text-zinc-500 font-normal">{user.username ? `@${user.username}` : 'no username'} · <span className="font-mono">{user.telegram_id}</span></div></div></div>}
        onClose={onClose}
      />
      <DialogBody className="space-y-6">
        <div className="grid grid-cols-3 gap-4">
          <Stat label="Quizzes created" value={user.quiz_count.toString()} />
          <Stat label="Total paid" value={formatUZS(user.total_paid_uzs)} />
          <Stat label="Language" value={<Badge tone="neutral">{user.language_code}</Badge>} />
        </div>

        <div className="rounded-lg border border-zinc-200 p-4">
          <div className="text-xs uppercase tracking-wider text-zinc-500 mb-2">Subscription</div>
          {user.subscription ? (
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <Badge tone="green" dot>{user.subscription.status}</Badge>
                <div className="text-sm">
                  <div className="font-medium text-zinc-900 capitalize">{user.subscription.plan} plan</div>
                  <div className="text-xs text-zinc-500">expires {formatDate(user.subscription.expires_at)}</div>
                </div>
              </div>
              <Button variant="outline" size="sm">Manage</Button>
            </div>
          ) : (
            <div className="text-sm text-zinc-500">No active subscription.</div>
          )}
        </div>

        <div className="rounded-lg border border-zinc-200 p-4">
          <div className="text-xs uppercase tracking-wider text-zinc-500 mb-3">Account</div>
          <div className="grid grid-cols-2 gap-y-2 text-sm">
            <div className="text-zinc-500">First seen</div>
            <div className="text-zinc-900 tnum">{formatDate(user.created_at, { year: 'numeric', month: 'short', day: 'numeric' })}</div>
            <div className="text-zinc-500">Last active</div>
            <div className="text-zinc-900 tnum">{formatDate(user.last_active_at, { year: 'numeric', month: 'short', day: 'numeric' })}</div>
            <div className="text-zinc-500">Status</div>
            <div>{user.is_blocked ? <Badge tone="red" dot>blocked</Badge> : <Badge tone="green" dot>active</Badge>}</div>
          </div>
        </div>
      </DialogBody>
      <DialogFooter>
        <Button variant="outline" onClick={onClose}>Close</Button>
        <Button variant={user.is_blocked ? 'default' : 'destructive'} onClick={() => onToggleBlock(user)}>
          {user.is_blocked ? <><IconRotate className="w-4 h-4" />Unblock user</> : <><IconBan className="w-4 h-4" />Block user</>}
        </Button>
      </DialogFooter>
    </Dialog>
  );
};

const Stat = ({ label, value }) => (
  <div className="rounded-lg border border-zinc-200 p-4">
    <div className="text-xs uppercase tracking-wider text-zinc-500">{label}</div>
    <div className="mt-2 text-xl font-semibold text-zinc-900 tnum">{value}</div>
  </div>
);

Object.assign(window, { UsersPage });
