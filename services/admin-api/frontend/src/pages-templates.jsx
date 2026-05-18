// Templates page — list of notification templates with inline edit

const TemplatesPage = () => {
  const templates = useStore(s => s.templates);
  const [expanded, setExpanded] = React.useState(null);
  const toast = useToast();

  const update = (slug, patch) => {
    store.set(s => ({
      ...s,
      templates: s.templates.map(t => t.slug === slug ? { ...t, ...patch } : t),
    }));
  };

  return (
    <div className="p-8 max-w-[1100px] mx-auto">
      <PageHeader
        title="Templates"
        description="Bot messages users receive at key moments. Edit text per language and toggle active state."
      />

      <div className="space-y-3">
        {templates.map(t => {
          const isOpen = expanded === t.slug;
          return (
            <Card key={t.slug}>
              <button
                onClick={() => setExpanded(isOpen ? null : t.slug)}
                className="w-full flex items-center gap-4 px-6 py-4 text-left"
              >
                <div className="w-9 h-9 rounded-md bg-zinc-100 flex items-center justify-center text-zinc-500 shrink-0">
                  <IconMessageSquare className="w-4 h-4" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-0.5">
                    <span className="text-sm font-semibold text-zinc-900">{t.name}</span>
                    <span className="text-xs font-mono text-zinc-500">{t.slug}</span>
                    {t.is_active
                      ? <Badge tone="green" dot>active</Badge>
                      : <Badge tone="neutral" dot>disabled</Badge>}
                  </div>
                  <div className="text-xs text-zinc-500">{t.description}</div>
                </div>
                <div onClick={e => e.stopPropagation()} className="shrink-0">
                  <Switch checked={t.is_active} onChange={(v) => { update(t.slug, { is_active: v }); toast.success(`${t.name} ${v ? 'enabled' : 'disabled'}`); }} />
                </div>
                <IconChevronDown className={cx('w-4 h-4 text-zinc-400 transition shrink-0', isOpen && 'rotate-180')} />
              </button>

              {isOpen && (
                <div className="border-t border-zinc-100 p-6 grid grid-cols-1 md:grid-cols-3 gap-4">
                  <TemplateField label="O‘zbek" code="uz" value={t.text_uz} onChange={v => update(t.slug, { text_uz: v })} />
                  <TemplateField label="Русский" code="ru" value={t.text_ru} onChange={v => update(t.slug, { text_ru: v })} />
                  <TemplateField label="English" code="en" value={t.text_en} onChange={v => update(t.slug, { text_en: v })} />
                  <div className="md:col-span-3 flex items-center justify-between">
                    <div className="text-xs text-zinc-500">Auto-saved. Variables: <code className="font-mono bg-zinc-100 px-1 rounded">{'{first_name}'}</code>, <code className="font-mono bg-zinc-100 px-1 rounded">{'{quiz_title}'}</code>, <code className="font-mono bg-zinc-100 px-1 rounded">{'{questions}'}</code>, <code className="font-mono bg-zinc-100 px-1 rounded">{'{days}'}</code></div>
                    <Button variant="outline" size="sm" onClick={() => toast.info('Sent test message to @farrukh_admin')}>
                      <IconSend className="w-3.5 h-3.5" />Send test
                    </Button>
                  </div>
                </div>
              )}
            </Card>
          );
        })}
      </div>
    </div>
  );
};

const TemplateField = ({ label, code, value, onChange }) => (
  <div>
    <div className="flex items-center gap-2 mb-1.5">
      <Label>{label}</Label>
      <Badge tone="neutral" className="font-mono">{code}</Badge>
    </div>
    <Textarea value={value} onChange={e => onChange(e.target.value)} className="min-h-[100px] font-mono text-[13px]" />
  </div>
);

Object.assign(window, { TemplatesPage });
