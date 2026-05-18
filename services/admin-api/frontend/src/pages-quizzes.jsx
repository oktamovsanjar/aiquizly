// Quizzes page

const QuizzesPage = () => {
  const quizzes = useStore(s => s.quizzes);
  const users = useStore(s => s.users);
  const [page, setPage] = React.useState(1);
  const [limit] = React.useState(10);
  const [filter, setFilter] = React.useState('all');
  const [sourceFilter, setSourceFilter] = React.useState('all');
  const [search, setSearch] = React.useState('');
  const [confirmDelete, setConfirmDelete] = React.useState(null);
  const toast = useToast();

  const userById = React.useMemo(() => {
    const m = {};
    users.forEach(u => { m[u.id] = u; });
    return m;
  }, [users]);

  const filtered = React.useMemo(() => {
    return quizzes.filter(q => {
      if (filter === 'public' && q.visibility !== 'public') return false;
      if (filter === 'private' && q.visibility !== 'private') return false;
      if (filter === 'deleted' && !q.deleted_at) return false;
      if (filter !== 'deleted' && q.deleted_at) return false;
      if (sourceFilter !== 'all' && q.source_type !== sourceFilter) return false;
      if (!search) return true;
      const s = search.toLowerCase();
      return q.title.toLowerCase().includes(s) || String(q.owner_id).includes(s);
    });
  }, [quizzes, filter, sourceFilter, search]);

  const total = filtered.length;
  const pages = Math.max(1, Math.ceil(total / limit));
  const slice = filtered.slice((page - 1) * limit, page * limit);
  React.useEffect(() => { setPage(1); }, [filter, sourceFilter, search]);

  const deleteQuiz = (q) => {
    store.set(s => ({
      ...s,
      quizzes: s.quizzes.map(x => x.id === q.id ? { ...x, deleted_at: new Date().toISOString() } : x),
    }));
    toast.success(`Deleted "${q.title}"`, {});
    setConfirmDelete(null);
  };
  const restoreQuiz = (q) => {
    store.set(s => ({
      ...s,
      quizzes: s.quizzes.map(x => x.id === q.id ? { ...x, deleted_at: null } : x),
    }));
    toast.success(`Restored "${q.title}"`);
  };
  const toggleVisibility = (q) => {
    const next = q.visibility === 'public' ? 'private' : 'public';
    store.set(s => ({
      ...s,
      quizzes: s.quizzes.map(x => x.id === q.id ? { ...x, visibility: next } : x),
    }));
    toast.success(`Set "${q.title}" to ${next}`);
  };

  const sourceLabel = {
    manual: 'Manual',
    ai_pdf: 'AI · PDF',
    ai_docx: 'AI · DOCX',
    ai_image: 'AI · Image',
    duplicated: 'Duplicated',
  };

  return (
    <div className="p-8 max-w-[1400px] mx-auto">
      <PageHeader
        title="Quizzes"
        description={<>{quizzes.filter(q => !q.deleted_at).length.toLocaleString()} active quizzes · {quizzes.filter(q => q.deleted_at).length} in trash</>}
      />

      <Card>
        <div className="flex items-center gap-3 p-4 border-b border-zinc-100 flex-wrap">
          <Tabs
            value={filter}
            onChange={setFilter}
            items={[
              { value: 'all',     label: 'All' },
              { value: 'public',  label: 'Public' },
              { value: 'private', label: 'Private' },
              { value: 'deleted', label: 'Trash' },
            ]}
          />
          <Input
            placeholder="Search quizzes…"
            value={search}
            onChange={e => setSearch(e.target.value)}
            leftIcon={<IconSearch className="w-4 h-4" />}
            className="max-w-xs"
          />
          <Select
            value={sourceFilter}
            onChange={setSourceFilter}
            options={[
              { value: 'all',        label: 'Source: All' },
              { value: 'manual',     label: 'Source: Manual' },
              { value: 'ai_pdf',     label: 'Source: AI PDF' },
              { value: 'ai_docx',    label: 'Source: AI DOCX' },
              { value: 'ai_image',   label: 'Source: AI Image' },
              { value: 'duplicated', label: 'Source: Duplicated' },
            ]}
            className="w-44"
          />
          <div className="flex-1" />
          <div className="text-xs text-zinc-500 tnum">{total} results</div>
        </div>

        <Table>
          <THead>
            <tr>
              <th>Title</th>
              <th>Owner</th>
              <th className="text-right">Questions</th>
              <th className="text-right">Plays</th>
              <th>Visibility</th>
              <th>Source</th>
              <th>Created</th>
              <th className="text-right">Actions</th>
            </tr>
          </THead>
          <TBody>
            {slice.map(q => {
              const owner = userById[q.owner_id];
              return (
                <TR key={q.id}>
                  <td className="py-3">
                    <div className="text-sm font-medium text-zinc-900">{q.title}</div>
                    <div className="text-xs text-zinc-500 font-mono">#{q.id}</div>
                  </td>
                  <td>
                    <div className="flex items-center gap-2 text-sm">
                      {owner && <Avatar name={`${owner.first_name} ${owner.last_name || ''}`} size="sm" />}
                      <span className="text-zinc-700">{q.owner_username ? `@${q.owner_username}` : <span className="font-mono">id{q.owner_id}</span>}</span>
                    </div>
                  </td>
                  <td className="text-right tnum text-sm">{q.questions_count}</td>
                  <td className="text-right tnum text-sm">{q.play_count.toLocaleString()}</td>
                  <td>
                    {q.visibility === 'public'
                      ? <Badge tone="green" dot>public</Badge>
                      : <Badge tone="yellow" dot>private</Badge>}
                  </td>
                  <td>
                    <span className="inline-flex items-center gap-1.5 text-xs text-zinc-600">
                      <span className="w-1.5 h-1.5 rounded-full bg-zinc-400" />
                      {sourceLabel[q.source_type] || q.source_type}
                    </span>
                  </td>
                  <td className="text-sm text-zinc-600 tnum">{formatDateShort(q.created_at)}</td>
                  <td className="text-right">
                    <div className="inline-flex items-center gap-1">
                      <Button variant="ghost" size="icon-sm" title={q.visibility === 'public' ? 'Make private' : 'Make public'} onClick={() => toggleVisibility(q)}>
                        {q.visibility === 'public' ? <IconEyeOff className="w-3.5 h-3.5" /> : <IconEye className="w-3.5 h-3.5" />}
                      </Button>
                      {q.deleted_at
                        ? <Button variant="ghost" size="icon-sm" title="Restore" onClick={() => restoreQuiz(q)}><IconRotate className="w-3.5 h-3.5" /></Button>
                        : <Button variant="ghost" size="icon-sm" title="Delete" onClick={() => setConfirmDelete(q)}><IconTrash className="w-3.5 h-3.5 text-red-600" /></Button>}
                    </div>
                  </td>
                </TR>
              );
            })}
            {slice.length === 0 && (
              <tr><td colSpan={8}><EmptyState icon={IconBookOpen} title="No quizzes here" description="Try a different filter, or wait — users create new quizzes all day." /></td></tr>
            )}
          </TBody>
        </Table>

        <Pagination page={page} pages={pages} total={total} limit={limit} onChange={setPage} />
      </Card>

      <Dialog open={!!confirmDelete} onClose={() => setConfirmDelete(null)} maxW="max-w-md">
        <DialogHeader title="Delete this quiz?" description="It will be moved to the trash. You can restore it later." onClose={() => setConfirmDelete(null)} />
        <DialogBody>
          {confirmDelete && (
            <div className="rounded-lg border border-zinc-200 p-4">
              <div className="text-sm font-medium text-zinc-900">{confirmDelete.title}</div>
              <div className="text-xs text-zinc-500 mt-1 font-mono">#{confirmDelete.id} · {confirmDelete.questions_count} questions · {confirmDelete.play_count.toLocaleString()} plays</div>
            </div>
          )}
        </DialogBody>
        <DialogFooter>
          <Button variant="outline" onClick={() => setConfirmDelete(null)}>Cancel</Button>
          <Button variant="destructive" onClick={() => deleteQuiz(confirmDelete)}>
            <IconTrash className="w-4 h-4" />Delete quiz
          </Button>
        </DialogFooter>
      </Dialog>
    </div>
  );
};

Object.assign(window, { QuizzesPage });
