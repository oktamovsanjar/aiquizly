// Settings page — real API for settings + admin management

const SettingsPage = () => {
  return (
    <div className="p-8 max-w-[1100px] mx-auto">
      <PageHeader
        title="Sozlamalar"
        description="Tizim konfiguratsiyasi va admin jamoasi."
      />
      <div className="space-y-6">
        <SystemSettings />
        <AdminManagement />
      </div>
    </div>
  );
};

const SystemSettings = () => {
  const [settings, setSettings] = React.useState({});
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState(null);
  const [editing, setEditing] = React.useState(null);
  const [draft, setDraft] = React.useState('');
  const [saving, setSaving] = React.useState(false);
  const toast = useToast();

  const loadSettings = () => {
    setLoading(true);
    setError(null);
    apiFetch('/settings')
      .then(data => {
        setSettings(data);
        setLoading(false);
      })
      .catch(err => {
        setError(err.message);
        setLoading(false);
      });
  };

  React.useEffect(() => { loadSettings(); }, []);

  const startEdit = (key, value) => {
    setEditing(key);
    setDraft(value);
  };

  const save = () => {
    setSaving(true);
    apiFetch(`/settings/${encodeURIComponent(editing)}`, {
      method: 'PUT',
      body: JSON.stringify({ value: draft }),
    })
      .then(() => {
        setSettings(s => ({
          ...s,
          [editing]: { ...s[editing], value: draft },
        }));
        toast.success(`${editing} saqlandi`);
        setEditing(null);
        setSaving(false);
      })
      .catch(err => {
        // Try to update locally even if API fails
        setSettings(s => ({
          ...s,
          [editing]: { ...s[editing], value: draft },
        }));
        toast.error(`Saqlashda xato: ${err.message}. Lokal yangilandi.`);
        setEditing(null);
        setSaving(false);
      });
  };

  const cancel = () => {
    setEditing(null);
    setDraft('');
  };

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle>Tizim konfiguratsiyasi</CardTitle>
            <CardDescription>Bot runtime tomonidan ishlatiladigan jonli qiymatlar.</CardDescription>
          </div>
          <Badge tone="neutral" className="font-mono"><IconBolt className="w-3 h-3" />jonli</Badge>
        </div>
      </CardHeader>
      <CardContent className="px-0 pb-0">
        {loading ? (
          <div className="flex items-center justify-center h-40 text-zinc-400 text-sm gap-2">
            <IconLoader className="w-5 h-5 animate-spin" />
            Yuklanmoqda...
          </div>
        ) : error ? (
          <div className="flex flex-col items-center justify-center h-40 gap-3">
            <div className="text-red-600 text-sm">{error}</div>
            <Button variant="outline" size="sm" onClick={loadSettings}>Qayta urinish</Button>
          </div>
        ) : Object.keys(settings).length === 0 ? (
          <div className="flex items-center justify-center h-40 text-zinc-400 text-sm">
            Sozlama topilmadi
          </div>
        ) : (
          <Table>
            <THead>
              <tr>
                <th>Kalit</th>
                <th>Qiymat</th>
                <th>Tavsif</th>
                <th className="text-right">Amallar</th>
              </tr>
            </THead>
            <TBody>
              {Object.entries(settings).map(([key, cfg]) => (
                <TR key={key}>
                  <td className="py-3 font-mono text-xs text-zinc-900">{key}</td>
                  <td>
                    {editing === key ? (
                      <div className="flex items-center gap-2">
                        <Input
                          value={draft}
                          onChange={e => setDraft(e.target.value)}
                          className="max-w-xs"
                          autoFocus
                          onKeyDown={e => { if (e.key === 'Enter') save(); if (e.key === 'Escape') cancel(); }}
                        />
                        <Button size="sm" onClick={save} disabled={saving}>
                          {saving ? <IconLoader className="w-3.5 h-3.5 animate-spin" /> : <IconCheck className="w-3.5 h-3.5" />}
                          Saqlash
                        </Button>
                        <Button size="sm" variant="ghost" onClick={cancel} disabled={saving}>Bekor</Button>
                      </div>
                    ) : (
                      <button
                        onClick={() => startEdit(key, cfg.value)}
                        className="font-mono text-sm text-zinc-900 bg-zinc-50 border border-zinc-200 rounded px-2 py-1 hover:bg-zinc-100 transition-colors"
                      >
                        {cfg.value}
                      </button>
                    )}
                  </td>
                  <td className="text-sm text-zinc-600 max-w-md">{cfg.description}</td>
                  <td className="text-right">
                    {editing !== key && (
                      <Button variant="ghost" size="sm" onClick={() => startEdit(key, cfg.value)}>
                        Tahrirlash
                      </Button>
                    )}
                  </td>
                </TR>
              ))}
            </TBody>
          </Table>
        )}
      </CardContent>
    </Card>
  );
};

const AdminManagement = () => {
  const [admins, setAdmins] = React.useState([]);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState(null);
  const [showAdd, setShowAdd] = React.useState(false);
  const [confirmRemove, setConfirmRemove] = React.useState(null);
  const [draft, setDraft] = React.useState({ telegram_id: '', username: '', role: 'admin' });
  const [submitting, setSubmitting] = React.useState(false);
  const [removing, setRemoving] = React.useState(false);
  const toast = useToast();

  const loadAdmins = () => {
    setLoading(true);
    setError(null);
    apiFetch('/admins')
      .then(data => {
        setAdmins(data.admins || data || []);
        setLoading(false);
      })
      .catch(err => {
        setError(err.message);
        setLoading(false);
      });
  };

  React.useEffect(() => { loadAdmins(); }, []);

  const submit = () => {
    if (!draft.telegram_id || !draft.username) {
      toast.error('Iltimos, ikkala maydonni ham to\'ldiring');
      return;
    }
    setSubmitting(true);
    apiFetch('/admins', {
      method: 'POST',
      body: JSON.stringify({
        telegram_id: parseInt(draft.telegram_id, 10),
        username: draft.username.replace(/^@/, ''),
        role: draft.role,
      }),
    })
      .then(newAdmin => {
        setAdmins(a => [...a, newAdmin]);
        toast.success(`@${newAdmin.username || draft.username} qo'shildi`);
        setShowAdd(false);
        setDraft({ telegram_id: '', username: '', role: 'admin' });
        setSubmitting(false);
      })
      .catch(err => {
        toast.error(`Qo'shishda xato: ${err.message}`);
        setSubmitting(false);
      });
  };

  const remove = (a) => {
    setRemoving(true);
    apiFetch(`/admins/${a.id}`, { method: 'DELETE' })
      .then(() => {
        setAdmins(list => list.filter(x => x.id !== a.id));
        toast.success(`@${a.username} o'chirildi`);
        setConfirmRemove(null);
        setRemoving(false);
      })
      .catch(err => {
        toast.error(`O'chirishda xato: ${err.message}`);
        setRemoving(false);
      });
  };

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle>Admin jamoasi</CardTitle>
            <CardDescription>Bu dashboardga kirish huquqiga ega odamlar.</CardDescription>
          </div>
          <Button onClick={() => setShowAdd(true)}>
            <IconPlus className="w-4 h-4" />Admin qo'shish
          </Button>
        </div>
      </CardHeader>
      <CardContent className="px-0 pb-0">
        {loading ? (
          <div className="flex items-center justify-center h-32 text-zinc-400 text-sm gap-2">
            <IconLoader className="w-5 h-5 animate-spin" />
            Yuklanmoqda...
          </div>
        ) : error ? (
          <div className="flex flex-col items-center justify-center h-32 gap-3">
            <div className="text-red-600 text-sm">{error}</div>
            <Button variant="outline" size="sm" onClick={loadAdmins}>Qayta urinish</Button>
          </div>
        ) : (
          <Table>
            <THead>
              <tr>
                <th>Admin</th>
                <th>Telegram ID</th>
                <th>Rol</th>
                <th>Qo'shilgan</th>
                <th className="text-right">Amallar</th>
              </tr>
            </THead>
            <TBody>
              {admins.map(a => (
                <TR key={a.id}>
                  <td className="py-3">
                    <div className="flex items-center gap-3">
                      <Avatar name={a.username || 'Admin'} size="md" />
                      <div>
                        <div className="text-sm font-medium text-zinc-900">@{a.username}</div>
                        <div className="text-xs text-zinc-500 font-mono">id {a.id}</div>
                      </div>
                    </div>
                  </td>
                  <td className="font-mono text-xs text-zinc-600 tnum">{a.telegram_id}</td>
                  <td>
                    {a.role === 'owner'   && <Badge tone="violet" dot>owner</Badge>}
                    {a.role === 'admin'   && <Badge tone="blue" dot>admin</Badge>}
                    {a.role === 'support' && <Badge tone="neutral" dot>support</Badge>}
                    {!['owner','admin','support'].includes(a.role) && <Badge tone="neutral" dot>{a.role}</Badge>}
                  </td>
                  <td className="text-sm text-zinc-600 tnum">
                    {a.created_at ? formatDate(a.created_at) : '—'}
                  </td>
                  <td className="text-right">
                    {a.role === 'owner' ? (
                      <span className="text-xs text-zinc-400">o'chirish mumkin emas</span>
                    ) : (
                      <Button variant="ghost" size="sm" onClick={() => setConfirmRemove(a)}>
                        <IconTrash className="w-3.5 h-3.5 text-red-600" />O'chirish
                      </Button>
                    )}
                  </td>
                </TR>
              ))}
              {admins.length === 0 && (
                <tr>
                  <td colSpan={5}>
                    <EmptyState icon={IconUsers} title="Admin topilmadi" description="" />
                  </td>
                </tr>
              )}
            </TBody>
          </Table>
        )}
      </CardContent>

      {/* Add admin dialog */}
      <Dialog open={showAdd} onClose={() => !submitting && setShowAdd(false)} maxW="max-w-md">
        <DialogHeader
          title="Admin qo'shish"
          description="U keyingi kirganida bu dashboardni ko'radi."
          onClose={() => !submitting && setShowAdd(false)}
        />
        <DialogBody className="space-y-4">
          <div>
            <Label>Telegram ID</Label>
            <Input
              className="mt-1.5"
              placeholder="312445001"
              value={draft.telegram_id}
              onChange={e => setDraft({ ...draft, telegram_id: e.target.value.replace(/\D/g, '') })}
            />
          </div>
          <div>
            <Label>Username</Label>
            <Input
              className="mt-1.5"
              placeholder="@username"
              value={draft.username}
              onChange={e => setDraft({ ...draft, username: e.target.value })}
            />
          </div>
          <div>
            <Label>Rol</Label>
            <Select
              value={draft.role}
              onChange={v => setDraft({ ...draft, role: v })}
              options={[
                { value: 'admin',   label: 'Admin · to\'liq kirish' },
                { value: 'support', label: 'Support · foydalanuvchilar va xabarlar' },
              ]}
              className="mt-1.5"
            />
          </div>
        </DialogBody>
        <DialogFooter>
          <Button variant="outline" onClick={() => setShowAdd(false)} disabled={submitting}>Bekor</Button>
          <Button onClick={submit} disabled={submitting}>
            {submitting ? <IconLoader className="w-4 h-4 animate-spin" /> : <IconPlus className="w-4 h-4" />}
            Admin qo'shish
          </Button>
        </DialogFooter>
      </Dialog>

      {/* Remove confirm dialog */}
      <Dialog open={!!confirmRemove} onClose={() => !removing && setConfirmRemove(null)} maxW="max-w-md">
        <DialogHeader
          title="Bu adminni o'chirish?"
          description="U darhol kirishdan mahrum bo'ladi."
          onClose={() => !removing && setConfirmRemove(null)}
        />
        <DialogBody>
          {confirmRemove && (
            <div className="rounded-lg border border-zinc-200 p-4 flex items-center gap-3">
              <Avatar name={confirmRemove.username || 'Admin'} size="md" />
              <div>
                <div className="text-sm font-medium">@{confirmRemove.username}</div>
                <div className="text-xs text-zinc-500 font-mono">{confirmRemove.telegram_id} · {confirmRemove.role}</div>
              </div>
            </div>
          )}
        </DialogBody>
        <DialogFooter>
          <Button variant="outline" onClick={() => setConfirmRemove(null)} disabled={removing}>Bekor</Button>
          <Button variant="destructive" onClick={() => remove(confirmRemove)} disabled={removing}>
            {removing ? <IconLoader className="w-4 h-4 animate-spin" /> : <IconTrash className="w-4 h-4" />}
            O'chirish
          </Button>
        </DialogFooter>
      </Dialog>
    </Card>
  );
};

Object.assign(window, { SettingsPage });
