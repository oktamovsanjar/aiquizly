// Quizzes page — real API, server-side visibility filter + pagination

const QUIZ_LIMIT = 20;

const QuizzesPage = () => {
  const [quizzes, setQuizzes] = React.useState([]);
  const [total, setTotal] = React.useState(0);
  const [page, setPage] = React.useState(1);
  const [filter, setFilter] = React.useState('all'); // all | public | private
  const [search, setSearch] = React.useState('');
  const [searchInput, setSearchInput] = React.useState('');
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState(null);
  const [confirmDelete, setConfirmDelete] = React.useState(null);
  const toast = useToast();

  const fetchQuizzes = React.useCallback((pg, vis, srch) => {
    setLoading(true);
    setError(null);
    const offset = (pg - 1) * QUIZ_LIMIT;
    let url = `/quizzes?limit=${QUIZ_LIMIT}&offset=${offset}`;
    if (vis === 'public') url += `&visibility=public`;
    else if (vis === 'private') url += `&visibility=private`;
    if (srch) url += `&search=${encodeURIComponent(srch)}`;

    apiFetch(url)
      .then(data => {
        const list = data.quizzes || data || [];
        setQuizzes(list);
        setTotal(data.total ?? list.length);
        setLoading(false);
      })
      .catch(err => {
        setError(err.message);
        setLoading(false);
      });
  }, []);

  React.useEffect(() => {
    fetchQuizzes(page, filter, search);
  }, [page, filter, search]);

  // Debounce search
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

  const pages = Math.max(1, Math.ceil(total / QUIZ_LIMIT));

  const doDelete = (quiz) => {
    apiFetch(`/quizzes/${quiz.id}`, { method: 'DELETE' })
      .then(() => {
        setQuizzes(prev => prev.filter(q => q.id !== quiz.id));
        setTotal(t => t - 1);
        setConfirmDelete(null);
        toast.success(`"${quiz.title}" o'chirildi`);
      })
      .catch(() => toast.error('O\'chirib bo\'lmadi'));
  };

  const sourceLabel = {
    manual: 'Manual',
    ai_pdf: 'AI · PDF',
    ai_docx: 'AI · DOCX',
    ai_image: 'AI · Rasm',
    duplicated: 'Nusxa',
  };

  return (
    <div className="p-8 max-w-[1400px] mx-auto">
      <PageHeader
        title="Quizlar"
        description={
          loading
            ? 'Yuklanmoqda...'
            : <><span className="tnum">{total.toLocaleString()}</span> ta quiz</>
        }
      />

      <Card>
        <div className="flex items-center gap-3 p-4 border-b border-zinc-100 flex-wrap">
          <Tabs
            value={filter}
            onChange={handleFilterChange}
            items={[
              { value: 'all',     label: 'Barchasi' },
              { value: 'public',  label: 'Ommaviy' },
              { value: 'private', label: 'Shaxsiy' },
            ]}
          />
          <Input
            placeholder="Quiz nomini qidiring…"
            value={searchInput}
            onChange={e => setSearchInput(e.target.value)}
            leftIcon={<IconSearch className="w-4 h-4" />}
            className="max-w-xs"
          />
          <div className="flex-1" />
          {!loading && <div className="text-xs text-zinc-500 tnum">{total} natija</div>}
        </div>

        {loading ? (
          <div className="flex items-center justify-center h-48 text-zinc-400 text-sm gap-2">
            <IconLoader className="w-5 h-5 animate-spin" />
            Yuklanmoqda...
          </div>
        ) : error ? (
          <div className="flex flex-col items-center justify-center h-48 gap-3">
            <div className="text-red-600 text-sm">{error}</div>
            <Button variant="outline" size="sm" onClick={() => fetchQuizzes(page, filter, search)}>
              Qayta urinish
            </Button>
          </div>
        ) : (
          <>
            <Table>
              <THead>
                <tr>
                  <th>Sarlavha</th>
                  <th>Egasi</th>
                  <th className="text-right">Savollar</th>
                  <th className="text-right">O'yinlar</th>
                  <th>Ko'rinish</th>
                  <th>Manba</th>
                  <th>Yaratilgan</th>
                  <th></th>
                </tr>
              </THead>
              <TBody>
                {quizzes.map(q => (
                  <TR key={q.id}>
                    <td className="py-3">
                      <div className="text-sm font-medium text-zinc-900">{q.title}</div>
                      <div className="text-xs text-zinc-500 font-mono">#{q.id}</div>
                    </td>
                    <td>
                      <div className="text-sm text-zinc-700 font-mono">
                        {q.owner_id ? `id${q.owner_id}` : '—'}
                      </div>
                    </td>
                    <td className="text-right tnum text-sm">
                      {q.total_questions ?? q.questions_count ?? '—'}
                    </td>
                    <td className="text-right tnum text-sm">
                      {(q.play_count || 0).toLocaleString()}
                    </td>
                    <td>
                      {q.visibility === 'public'
                        ? <Badge tone="green" dot>ommaviy</Badge>
                        : <Badge tone="yellow" dot>shaxsiy</Badge>}
                    </td>
                    <td>
                      {q.source_type ? (
                        <span className="inline-flex items-center gap-1.5 text-xs text-zinc-600">
                          <span className="w-1.5 h-1.5 rounded-full bg-zinc-400" />
                          {sourceLabel[q.source_type] || q.source_type}
                        </span>
                      ) : '—'}
                    </td>
                    <td className="text-sm text-zinc-600 tnum">
                      {q.created_at ? formatDateShort(q.created_at) : '—'}
                    </td>
                    <td className="text-right" onClick={e => e.stopPropagation()}>
                      <Button variant="ghost" size="sm" onClick={() => setConfirmDelete(q)}>
                        <IconTrash className="w-3.5 h-3.5 text-red-500" />
                      </Button>
                    </td>
                  </TR>
                ))}
                {quizzes.length === 0 && (
                  <tr>
                    <td colSpan={7}>
                      <EmptyState
                        icon={IconBookOpen}
                        title="Quiz topilmadi"
                        description="Boshqa filtr yoki qidiruv so'zini sinab ko'ring."
                      />
                    </td>
                  </tr>
                )}
              </TBody>
            </Table>

            <Pagination page={page} pages={pages} total={total} limit={QUIZ_LIMIT} onChange={setPage} />
          </>
        )}
      </Card>
      <DeleteQuizDialog quiz={confirmDelete} onConfirm={doDelete} onClose={() => setConfirmDelete(null)} />
    </div>
  );
};

// Delete confirmation dialog
const DeleteQuizDialog = ({ quiz, onConfirm, onClose }) => {
  if (!quiz) return null;
  return (
    <Dialog open={!!quiz} onClose={onClose} maxW="max-w-md">
      <DialogHeader title="Quizni o'chirish" onClose={onClose} />
      <DialogBody>
        <p className="text-sm text-zinc-700">
          <span className="font-semibold">"{quiz.title}"</span> quizini o'chirmoqchimisiz?
          Ushbu amal qaytarib bo'lmaydi.
        </p>
      </DialogBody>
      <DialogFooter>
        <Button variant="outline" onClick={onClose}>Bekor qilish</Button>
        <Button variant="destructive" onClick={() => onConfirm(quiz)}>
          <IconTrash className="w-4 h-4" /> Ha, o'chir
        </Button>
      </DialogFooter>
    </Dialog>
  );
};

Object.assign(window, { QuizzesPage });
