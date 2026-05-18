// Settings page — key-value settings + admin management

const SettingsPage = () => {
  return (
    <div className="p-8 max-w-[1100px] mx-auto">
      <PageHeader
        title="Settings"
        description="System config and admin team."
      />
      <div className="space-y-6">
        <SystemSettings />
        <AdminManagement />
      </div>
    </div>
  );
};

const SystemSettings = () => {
  const settings = useStore(s => s.settings);
  const [editing, setEditing] = React.useState(null);
  const [draft, setDraft] = React.useState('');
  const toast = useToast();

  const startEdit = (key, value) => { setEditing(key); setDraft(value); };
  const save = () => {
    store.set(s => ({
      ...s,
      settings: { ...s.settings, [editing]: { ...s.settings[editing], value: draft } },
    }));
    toast.success(`Saved ${editing}`);
    setEditing(null);
  };

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle>System configuration</CardTitle>
            <CardDescription>Live values used by the bot runtime.</CardDescription>
          </div>
          <Badge tone="neutral" className="font-mono"><IconBolt className="w-3 h-3" />live</Badge>
        </div>
      </CardHeader>
      <CardContent className="px-0 pb-0">
        <Table>
          <THead>
            <tr>
              <th>Key</th>
              <th>Value</th>
              <th>Description</th>
              <th className="text-right">Actions</th>
            </tr>
          </THead>
          <TBody>
            {Object.entries(settings).map(([key, cfg]) => (
              <TR key={key}>
                <td className="py-3 font-mono text-xs text-zinc-900">{key}</td>
                <td>
                  {editing === key ? (
                    <div className="flex items-center gap-2">
                      <Input value={draft} onChange={e => setDraft(e.target.value)} className="max-w-xs" autoFocus />
                      <Button size="sm" onClick={save}><IconCheck className="w-3.5 h-3.5" />Save</Button>
                      <Button size="sm" variant="ghost" onClick={() => setEditing(null)}>Cancel</Button>
                    </div>
                  ) : (
                    <button onClick={() => startEdit(key, cfg.value)} className="font-mono text-sm text-zinc-900 bg-zinc-50 border border-zinc-200 rounded px-2 py-1 hover:bg-zinc-100">
                      {cfg.value}
                    </button>
                  )}
                </td>
                <td className="text-sm text-zinc-600 max-w-md">{cfg.description}</td>
                <td className="text-right">
                  {editing !== key && (
                    <Button variant="ghost" size="sm" onClick={() => startEdit(key, cfg.value)}>Edit</Button>
                  )}
                </td>
              </TR>
            ))}
          </TBody>
        </Table>
      </CardContent>
    </Card>
  );
};

const AdminManagement = () => {
  const admins = useStore(s => s.admins);
  const [showAdd, setShowAdd] = React.useState(false);
  const [confirmRemove, setConfirmRemove] = React.useState(null);
  const [draft, setDraft] = React.useState({ telegram_id: '', username: '', role: 'admin' });
  const toast = useToast();

  const submit = () => {
    if (!draft.telegram_id || !draft.username) { toast.error('Please fill both fields'); return; }
    const newAdmin = {
      id: Math.max(...admins.map(a => a.id)) + 1,
      telegram_id: parseInt(draft.telegram_id, 10),
      username: draft.username.replace(/^@/, ''),
      role: draft.role,
      created_at: new Date().toISOString(),
    };
    store.set(s => ({ ...s, admins: [...s.admins, newAdmin] }));
    toast.success(`Added @${newAdmin.username} as ${newAdmin.role}`);
    setShowAdd(false);
    setDraft({ telegram_id: '', username: '', role: 'admin' });
  };
  const remove = (a) => {
    store.set(s => ({ ...s, admins: s.admins.filter(x => x.id !== a.id) }));
    toast.success(`Removed @${a.username}`);
    setConfirmRemove(null);
  };

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle>Admin team</CardTitle>
            <CardDescription>People who can access this dashboard.</CardDescription>
          </div>
          <Button onClick={() => setShowAdd(true)}><IconPlus className="w-4 h-4" />Add admin</Button>
        </div>
      </CardHeader>
      <CardContent className="px-0 pb-0">
        <Table>
          <THead>
            <tr>
              <th>Admin</th>
              <th>Telegram ID</th>
              <th>Role</th>
              <th>Added</th>
              <th className="text-right">Actions</th>
            </tr>
          </THead>
          <TBody>
            {admins.map(a => (
              <TR key={a.id}>
                <td className="py-3">
                  <div className="flex items-center gap-3">
                    <Avatar name={a.username} size="md" />
                    <div>
                      <div className="text-sm font-medium text-zinc-900">@{a.username}</div>
                      <div className="text-xs text-zinc-500 font-mono">id {a.id}</div>
                    </div>
                  </div>
                </td>
                <td className="font-mono text-xs text-zinc-600 tnum">{a.telegram_id}</td>
                <td>
                  {a.role === 'owner' && <Badge tone="violet" dot>owner</Badge>}
                  {a.role === 'admin' && <Badge tone="blue" dot>admin</Badge>}
                  {a.role === 'support' && <Badge tone="neutral" dot>support</Badge>}
                </td>
                <td className="text-sm text-zinc-600 tnum">{formatDate(a.created_at)}</td>
                <td className="text-right">
                  {a.role === 'owner' ? (
                    <span className="text-xs text-zinc-400">cannot remove</span>
                  ) : (
                    <Button variant="ghost" size="sm" onClick={() => setConfirmRemove(a)}>
                      <IconTrash className="w-3.5 h-3.5 text-red-600" />Remove
                    </Button>
                  )}
                </td>
              </TR>
            ))}
          </TBody>
        </Table>
      </CardContent>

      <Dialog open={showAdd} onClose={() => setShowAdd(false)} maxW="max-w-md">
        <DialogHeader title="Add admin" description="They'll see this dashboard the next time they sign in." onClose={() => setShowAdd(false)} />
        <DialogBody className="space-y-4">
          <div>
            <Label>Telegram ID</Label>
            <Input className="mt-1.5" placeholder="312445001" value={draft.telegram_id}
              onChange={e => setDraft({ ...draft, telegram_id: e.target.value.replace(/\D/g, '') })} />
          </div>
          <div>
            <Label>Username</Label>
            <Input className="mt-1.5" placeholder="@username" value={draft.username}
              onChange={e => setDraft({ ...draft, username: e.target.value })} />
          </div>
          <div>
            <Label>Role</Label>
            <Select
              value={draft.role}
              onChange={v => setDraft({ ...draft, role: v })}
              options={[
                { value: 'admin', label: 'Admin · full access' },
                { value: 'support', label: 'Support · users & notifications only' },
              ]}
              className="mt-1.5"
            />
          </div>
        </DialogBody>
        <DialogFooter>
          <Button variant="outline" onClick={() => setShowAdd(false)}>Cancel</Button>
          <Button onClick={submit}><IconPlus className="w-4 h-4" />Add admin</Button>
        </DialogFooter>
      </Dialog>

      <Dialog open={!!confirmRemove} onClose={() => setConfirmRemove(null)} maxW="max-w-md">
        <DialogHeader title="Remove this admin?" description="They will lose access immediately." onClose={() => setConfirmRemove(null)} />
        <DialogBody>
          {confirmRemove && (
            <div className="rounded-lg border border-zinc-200 p-4 flex items-center gap-3">
              <Avatar name={confirmRemove.username} size="md" />
              <div>
                <div className="text-sm font-medium">@{confirmRemove.username}</div>
                <div className="text-xs text-zinc-500 font-mono">{confirmRemove.telegram_id} · {confirmRemove.role}</div>
              </div>
            </div>
          )}
        </DialogBody>
        <DialogFooter>
          <Button variant="outline" onClick={() => setConfirmRemove(null)}>Cancel</Button>
          <Button variant="destructive" onClick={() => remove(confirmRemove)}><IconTrash className="w-4 h-4" />Remove</Button>
        </DialogFooter>
      </Dialog>
    </Card>
  );
};

Object.assign(window, { SettingsPage });
