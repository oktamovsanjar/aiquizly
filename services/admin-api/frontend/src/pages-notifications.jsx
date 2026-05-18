// Notifications page — Broadcast composer + History

const NotificationsPage = () => {
  const [tab, setTab] = React.useState('broadcast');
  const notifications = useStore(s => s.notifications);

  return (
    <div className="p-8 max-w-[1400px] mx-auto">
      <PageHeader
        title="Notifications"
        description="Send broadcasts to your bot users and review past sends."
      />
      <div className="mb-5">
        <Tabs
          value={tab}
          onChange={setTab}
          items={[
            { value: 'broadcast', label: 'Broadcast' },
            { value: 'history',   label: 'History', count: notifications.length },
          ]}
        />
      </div>
      {tab === 'broadcast' && <Broadcast />}
      {tab === 'history' && <History />}
    </div>
  );
};

const Broadcast = () => {
  const users = useStore(s => s.users);
  const [text, setText] = React.useState('');
  const [language, setLanguage] = React.useState('all');
  const [audience, setAudience] = React.useState('all');
  const [parseMode, setParseMode] = React.useState('html');
  const [sending, setSending] = React.useState(false);
  const [confirm, setConfirm] = React.useState(false);
  const toast = useToast();

  const langCount = (l) => l === 'all' ? users.length : users.filter(u => u.language_code === l).length;
  const audienceCount = audience === 'all'
    ? langCount(language)
    : audience === 'active'
      ? users.filter(u => !u.is_blocked && (language === 'all' || u.language_code === language)).length
      : users.filter(u => u.subscription && (language === 'all' || u.language_code === language)).length;

  const send = () => {
    setSending(true);
    setTimeout(() => {
      const newOne = {
        id: 7100 + Math.floor(Math.random() * 999),
        text,
        language_code: language,
        recipients: audienceCount,
        delivered: audienceCount,
        failed: 0,
        status: 'completed',
        created_at: new Date().toISOString(),
        sent_by: 'farrukh_admin',
      };
      store.set(s => ({ ...s, notifications: [newOne, ...s.notifications] }));
      setSending(false);
      setConfirm(false);
      setText('');
      toast.success(`Broadcast queued to ${audienceCount.toLocaleString()} users`);
    }, 1200);
  };

  return (
    <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
      <Card className="xl:col-span-2">
        <CardHeader>
          <CardTitle>Compose broadcast</CardTitle>
          <CardDescription>This message will be sent to every user matching your filters.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-5">
          <div>
            <Label>Message</Label>
            <Textarea
              placeholder="Hello {first_name}! We just shipped something new — try it out 🎉"
              value={text}
              onChange={e => setText(e.target.value)}
              className="mt-1.5 min-h-[160px] font-mono text-[13px]"
              maxLength={4000}
            />
            <div className="flex items-center justify-between mt-1.5">
              <div className="text-xs text-zinc-500">Variables: <code className="font-mono bg-zinc-100 px-1 rounded">{'{first_name}'}</code>, <code className="font-mono bg-zinc-100 px-1 rounded">{'{username}'}</code></div>
              <div className="text-xs text-zinc-500 tnum">{text.length} / 4000</div>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label>Language</Label>
              <Select
                value={language}
                onChange={setLanguage}
                options={[
                  { value: 'all', label: `All languages · ${langCount('all').toLocaleString()}` },
                  { value: 'uz',  label: `O‘zbek · ${langCount('uz').toLocaleString()}` },
                  { value: 'ru',  label: `Русский · ${langCount('ru').toLocaleString()}` },
                  { value: 'en',  label: `English · ${langCount('en').toLocaleString()}` },
                ]}
                className="mt-1.5"
              />
            </div>
            <div>
              <Label>Audience</Label>
              <Select
                value={audience}
                onChange={setAudience}
                options={[
                  { value: 'all',          label: 'All users' },
                  { value: 'active',       label: 'Active (non-blocked)' },
                  { value: 'subscribers',  label: 'Subscribers only' },
                ]}
                className="mt-1.5"
              />
            </div>
          </div>

          <div>
            <Label>Parse mode</Label>
            <div className="mt-1.5 inline-flex rounded-md border border-zinc-200 overflow-hidden">
              {['plain', 'html', 'markdown'].map(m => (
                <button
                  key={m}
                  onClick={() => setParseMode(m)}
                  className={cx('px-3 h-9 text-sm', parseMode === m ? 'bg-zinc-900 text-white' : 'bg-white text-zinc-700 hover:bg-zinc-50', 'capitalize')}
                >
                  {m}
                </button>
              ))}
            </div>
          </div>
        </CardContent>
        <CardFooter className="justify-between">
          <div className="text-sm text-zinc-600">
            Will be sent to <span className="font-semibold text-zinc-900 tnum">{audienceCount.toLocaleString()}</span> users
          </div>
          <div className="flex items-center gap-2">
            <Button variant="outline" disabled={!text.trim()}>Save as draft</Button>
            <Button onClick={() => setConfirm(true)} disabled={!text.trim()}>
              <IconSend className="w-4 h-4" />Send broadcast
            </Button>
          </div>
        </CardFooter>
      </Card>

      {/* Preview */}
      <Card>
        <CardHeader>
          <CardTitle>Preview</CardTitle>
          <CardDescription>How it appears in the user's chat.</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="rounded-xl bg-zinc-100 border border-zinc-200 p-4">
            <div className="flex items-center gap-2 mb-3 text-xs text-zinc-500">
              <div className="w-8 h-8 rounded-full bg-zinc-900 text-white flex items-center justify-center text-sm font-bold">Q</div>
              <div>
                <div className="font-medium text-zinc-900">Quizly bot</div>
                <div className="text-[11px]">bot · online</div>
              </div>
            </div>
            <div className="bg-white rounded-2xl rounded-tl-md p-3 text-sm text-zinc-900 whitespace-pre-wrap shadow-card max-w-full break-words">
              {text || <span className="text-zinc-400">Your message will appear here…</span>}
            </div>
            <div className="text-[10px] text-zinc-400 mt-1 pl-1">via @QuizlyBot · 12:42</div>
          </div>
          <div className="mt-4 text-xs text-zinc-500 space-y-1.5">
            <div className="flex items-center justify-between"><span>Estimated cost</span> <span className="tnum text-zinc-900">~{Math.ceil(audienceCount / 25)} s</span></div>
            <div className="flex items-center justify-between"><span>API rate</span> <span className="tnum text-zinc-900">25 msg/s</span></div>
            <div className="flex items-center justify-between"><span>Parse mode</span> <span className="text-zinc-900 capitalize">{parseMode}</span></div>
          </div>
        </CardContent>
      </Card>

      <Dialog open={confirm} onClose={() => !sending && setConfirm(false)} maxW="max-w-md">
        <DialogHeader title="Send this broadcast?" description="This action cannot be undone." onClose={() => !sending && setConfirm(false)} />
        <DialogBody>
          <div className="rounded-lg border border-zinc-200 p-4 mb-3">
            <div className="text-xs uppercase tracking-wider text-zinc-500 mb-2">Message</div>
            <div className="text-sm text-zinc-900 whitespace-pre-wrap break-words max-h-32 overflow-y-auto">{text}</div>
          </div>
          <div className="text-sm text-zinc-700">
            Will be delivered to <span className="font-semibold tnum">{audienceCount.toLocaleString()}</span> users
            {language !== 'all' && <> with language <Badge tone="neutral" className="ml-1">{language}</Badge></>}
          </div>
        </DialogBody>
        <DialogFooter>
          <Button variant="outline" onClick={() => setConfirm(false)} disabled={sending}>Cancel</Button>
          <Button onClick={send} disabled={sending}>
            {sending ? <IconLoader className="w-4 h-4 animate-spin" /> : <IconSend className="w-4 h-4" />}
            {sending ? 'Sending…' : 'Send now'}
          </Button>
        </DialogFooter>
      </Dialog>
    </div>
  );
};

const History = () => {
  const notifications = useStore(s => s.notifications);
  const [page, setPage] = React.useState(1);
  const limit = 10;
  const pages = Math.max(1, Math.ceil(notifications.length / limit));
  const slice = notifications.slice((page - 1) * limit, page * limit);

  return (
    <Card>
      <CardHeader>
        <CardTitle>Past broadcasts</CardTitle>
        <CardDescription>Most recent on top.</CardDescription>
      </CardHeader>
      <CardContent className="px-0 pb-0">
        <ul className="divide-y divide-zinc-100">
          {slice.map(n => {
            const successRate = n.recipients > 0 ? (n.delivered / n.recipients) * 100 : 0;
            return (
              <li key={n.id} className="px-6 py-4 flex items-start gap-4">
                <div className="w-9 h-9 rounded-full bg-zinc-100 flex items-center justify-center text-zinc-500 shrink-0">
                  <IconSend className="w-4 h-4" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1 flex-wrap">
                    {n.status === 'sending'
                      ? <Badge tone="yellow"><IconLoader className="w-3 h-3 animate-spin" />sending</Badge>
                      : <Badge tone="green" dot>completed</Badge>}
                    <Badge tone="neutral">{n.language_code}</Badge>
                    <span className="text-xs text-zinc-500">by @{n.sent_by}</span>
                    <span className="text-xs text-zinc-500 ml-auto tnum">{formatRelative(n.created_at)}</span>
                  </div>
                  <div className="text-sm text-zinc-900 line-clamp-2">{n.text}</div>
                  <div className="mt-2 flex items-center gap-4 text-xs text-zinc-500 tnum">
                    <span><span className="text-zinc-900 font-medium">{n.recipients.toLocaleString()}</span> recipients</span>
                    <span><span className="text-emerald-600 font-medium">{n.delivered.toLocaleString()}</span> delivered</span>
                    {n.failed > 0 && <span><span className="text-red-600 font-medium">{n.failed}</span> failed</span>}
                    <span className="ml-auto">{successRate.toFixed(1)}% success</span>
                  </div>
                </div>
              </li>
            );
          })}
        </ul>
        <Pagination page={page} pages={pages} total={notifications.length} limit={limit} onChange={setPage} />
      </CardContent>
    </Card>
  );
};

Object.assign(window, { NotificationsPage });
