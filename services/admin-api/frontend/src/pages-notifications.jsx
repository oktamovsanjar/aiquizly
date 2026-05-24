// Notifications page — Broadcast composer + History (mock history, real UI)

const MOCK_HISTORY = [
  {
    id: 7001,
    text: "Yangi yangilanish: AI import endi rasm fayllarini ham qo'llab-quvvatlaydi 🚀",
    language_code: 'uz',
    recipients: 1213,
    delivered: 1198,
    failed: 15,
    status: 'completed',
    created_at: new Date(Date.now() - 2 * 86400 * 1000).toISOString(),
    sent_by: 'admin',
  },
  {
    id: 7002,
    text: 'Праздничная акция: подписка на 30% дешевле до конца недели!',
    language_code: 'ru',
    recipients: 842,
    delivered: 831,
    failed: 11,
    status: 'completed',
    created_at: new Date(Date.now() - 5 * 86400 * 1000).toISOString(),
    sent_by: 'admin',
  },
  {
    id: 7003,
    text: 'New feature: leaderboards are now available for public quizzes.',
    language_code: 'en',
    recipients: 304,
    delivered: 301,
    failed: 3,
    status: 'completed',
    created_at: new Date(Date.now() - 9 * 86400 * 1000).toISOString(),
    sent_by: 'admin',
  },
  {
    id: 7004,
    text: 'Texnik ish: bugun 03:00 dan 04:00 gacha bot ishlamasligi mumkin.',
    language_code: 'all',
    recipients: 2350,
    delivered: 2301,
    failed: 49,
    status: 'completed',
    created_at: new Date(Date.now() - 14 * 86400 * 1000).toISOString(),
    sent_by: 'admin',
  },
];

const NotificationsPage = () => {
  const [tab, setTab] = React.useState('broadcast');
  const [history, setHistory] = React.useState(MOCK_HISTORY);

  const addToHistory = (item) => {
    setHistory(h => [item, ...h]);
  };

  return (
    <div className="p-8 max-w-[1400px] mx-auto">
      <PageHeader
        title="Xabarnomalar"
        description="Foydalanuvchilarga broadcast yuboring va o&#39;tgan yuborishlarni ko&#39;ring."
      />
      <div className="mb-5">
        <Tabs
          value={tab}
          onChange={setTab}
          items={[
            { value: 'broadcast', label: 'Broadcast' },
            { value: 'history',   label: 'Tarix', count: history.length },
          ]}
        />
      </div>
      {tab === 'broadcast' && <Broadcast onSent={addToHistory} />}
      {tab === 'history'   && <History notifications={history} />}
    </div>
  );
};

const Broadcast = ({ onSent }) => {
  const [text, setText] = React.useState('');
  const [language, setLanguage] = React.useState('all');
  const [audience, setAudience] = React.useState('all');
  const [parseMode, setParseMode] = React.useState('html');
  const [sending, setSending] = React.useState(false);
  const [confirm, setConfirm] = React.useState(false);
  const toast = useToast();

  const send = () => {
    setSending(true);
    // Simulate sending — no real broadcast API endpoint in spec
    setTimeout(() => {
      const item = {
        id: Date.now(),
        text,
        language_code: language,
        recipients: 0,
        delivered: 0,
        failed: 0,
        status: 'completed',
        created_at: new Date().toISOString(),
        sent_by: 'admin',
      };
      onSent(item);
      setSending(false);
      setConfirm(false);
      setText('');
      toast.success("Broadcast navbatga qo'yildi");
    }, 1200);
  };

  return (
    <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
      <Card className="xl:col-span-2">
        <CardHeader>
          <CardTitle>Broadcast yaratish</CardTitle>
          <CardDescription>Bu xabar sizning filtrlaringizga mos kelgan har bir foydalanuvchiga yuboriladi.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-5">
          <div>
            <Label>Xabar</Label>
            <Textarea
              placeholder="Salom {first_name}! Yangi narsa chiqardik — sinab ko&#39;ring 🎉"
              value={text}
              onChange={e => setText(e.target.value)}
              className="mt-1.5 min-h-[160px] font-mono text-[13px]"
              maxLength={4000}
            />
            <div className="flex items-center justify-between mt-1.5">
              <div className="text-xs text-zinc-500">
                O'zgaruvchilar: <code className="font-mono bg-zinc-100 px-1 rounded">{'{first_name}'}</code>, <code className="font-mono bg-zinc-100 px-1 rounded">{'{username}'}</code>
              </div>
              <div className="text-xs text-zinc-500 tnum">{text.length} / 4000</div>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label>Til</Label>
              <Select
                value={language}
                onChange={setLanguage}
                options={[
                  { value: 'all', label: 'Barcha tillar' },
                  { value: 'uz',  label: "O'zbek" },
                  { value: 'ru',  label: 'Русский' },
                  { value: 'en',  label: 'English' },
                ]}
                className="mt-1.5"
              />
            </div>
            <div>
              <Label>Auditoriya</Label>
              <Select
                value={audience}
                onChange={setAudience}
                options={[
                  { value: 'all',         label: 'Barcha foydalanuvchilar' },
                  { value: 'active',      label: 'Faollar (bloklanmaganlar)' },
                  { value: 'subscribers', label: 'Faqat obunachilар' },
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
                  className={cx(
                    'px-3 h-9 text-sm capitalize',
                    parseMode === m ? 'bg-zinc-900 text-white' : 'bg-white text-zinc-700 hover:bg-zinc-50'
                  )}
                >
                  {m}
                </button>
              ))}
            </div>
          </div>
        </CardContent>
        <CardFooter className="justify-between">
          <div className="text-sm text-zinc-600">
            Broadcast tayyor
          </div>
          <div className="flex items-center gap-2">
            <Button variant="outline" disabled={!text.trim()}>Qoralama saqlash</Button>
            <Button onClick={() => setConfirm(true)} disabled={!text.trim()}>
              <IconSend className="w-4 h-4" />Broadcast yuborish
            </Button>
          </div>
        </CardFooter>
      </Card>

      {/* Preview */}
      <Card>
        <CardHeader>
          <CardTitle>Ko'rinish</CardTitle>
          <CardDescription>Foydalanuvchi chatida qanday ko'rinadi.</CardDescription>
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
            <div className="bg-white rounded-2xl rounded-tl-md p-3 text-sm text-zinc-900 whitespace-pre-wrap shadow-card max-w-full break-words min-h-[48px]">
              {text || <span className="text-zinc-400">Xabaringiz shu yerda ko'rinadi…</span>}
            </div>
            <div className="text-[10px] text-zinc-400 mt-1 pl-1">@QuizlyBot orqali · {new Date().toLocaleTimeString('uz', { hour: '2-digit', minute: '2-digit' })}</div>
          </div>
          <div className="mt-4 text-xs text-zinc-500 space-y-1.5">
            <div className="flex items-center justify-between">
              <span>Parse mode</span>
              <span className="text-zinc-900 capitalize">{parseMode}</span>
            </div>
            <div className="flex items-center justify-between">
              <span>Til</span>
              <span className="text-zinc-900">{language === 'all' ? 'Barchasi' : language.toUpperCase()}</span>
            </div>
            <div className="flex items-center justify-between">
              <span>Auditoriya</span>
              <span className="text-zinc-900 capitalize">{audience}</span>
            </div>
          </div>
        </CardContent>
      </Card>

      <Dialog open={confirm} onClose={() => !sending && setConfirm(false)} maxW="max-w-md">
        <DialogHeader
          title="Bu broadcastni yuborish?"
          description="Bu amalni bekor qilib bo&#39;lmaydi."
          onClose={() => !sending && setConfirm(false)}
        />
        <DialogBody>
          <div className="rounded-lg border border-zinc-200 p-4 mb-3">
            <div className="text-xs uppercase tracking-wider text-zinc-500 mb-2">Xabar</div>
            <div className="text-sm text-zinc-900 whitespace-pre-wrap break-words max-h-32 overflow-y-auto">{text}</div>
          </div>
          <div className="text-sm text-zinc-700 space-y-1">
            {language !== 'all' && (
              <div>Til: <Badge tone="neutral" className="ml-1">{language}</Badge></div>
            )}
            <div>Auditoriya: <span className="font-medium">{audience}</span></div>
          </div>
        </DialogBody>
        <DialogFooter>
          <Button variant="outline" onClick={() => setConfirm(false)} disabled={sending}>Bekor</Button>
          <Button onClick={send} disabled={sending}>
            {sending ? <IconLoader className="w-4 h-4 animate-spin" /> : <IconSend className="w-4 h-4" />}
            {sending ? 'Yuborilmoqda…' : 'Hozir yuborish'}
          </Button>
        </DialogFooter>
      </Dialog>
    </div>
  );
};

const History = ({ notifications }) => {
  const [page, setPage] = React.useState(1);
  const limit = 10;
  const pages = Math.max(1, Math.ceil(notifications.length / limit));
  const slice = notifications.slice((page - 1) * limit, page * limit);

  return (
    <Card>
      <CardHeader>
        <CardTitle>O'tgan broadcastlar</CardTitle>
        <CardDescription>Eng yangi yuqorida.</CardDescription>
      </CardHeader>
      <CardContent className="px-0 pb-0">
        {notifications.length === 0 ? (
          <div className="flex items-center justify-center h-32 text-zinc-400 text-sm">
            Hali broadcast yuborilmagan
          </div>
        ) : (
          <ul className="divide-y divide-zinc-100">
            {slice.map(n => {
              const successRate = n.recipients > 0 ? (n.delivered / n.recipients) * 100 : 100;
              return (
                <li key={n.id} className="px-6 py-4 flex items-start gap-4">
                  <div className="w-9 h-9 rounded-full bg-zinc-100 flex items-center justify-center text-zinc-500 shrink-0">
                    <IconSend className="w-4 h-4" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1 flex-wrap">
                      {n.status === 'sending'
                        ? <Badge tone="yellow"><IconLoader className="w-3 h-3 animate-spin" />yuborilmoqda</Badge>
                        : <Badge tone="green" dot>tugallandi</Badge>}
                      {n.language_code && <Badge tone="neutral">{n.language_code}</Badge>}
                      {n.sent_by && <span className="text-xs text-zinc-500">by @{n.sent_by}</span>}
                      <span className="text-xs text-zinc-500 ml-auto tnum">{formatRelative(n.created_at)}</span>
                    </div>
                    <div className="text-sm text-zinc-900 line-clamp-2">{n.text}</div>
                    {n.recipients > 0 && (
                      <div className="mt-2 flex items-center gap-4 text-xs text-zinc-500 tnum">
                        <span><span className="text-zinc-900 font-medium">{n.recipients.toLocaleString()}</span> oluvchi</span>
                        <span><span className="text-emerald-600 font-medium">{n.delivered.toLocaleString()}</span> yetkazildi</span>
                        {n.failed > 0 && <span><span className="text-red-600 font-medium">{n.failed}</span> xato</span>}
                        <span className="ml-auto">{successRate.toFixed(1)}% muvaffaqiyat</span>
                      </div>
                    )}
                  </div>
                </li>
              );
            })}
          </ul>
        )}
        <Pagination page={page} pages={pages} total={notifications.length} limit={limit} onChange={setPage} />
      </CardContent>
    </Card>
  );
};

Object.assign(window, { NotificationsPage });
