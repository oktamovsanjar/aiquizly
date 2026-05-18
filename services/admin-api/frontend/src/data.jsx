// Mock data + in-memory "API" state for the prototype.
// Data is deterministic (seeded RNG) so reloads are stable.

// ---- seeded RNG ------------------------------------------------------------
function mulberry32(seed) {
  return function() {
    let t = seed += 0x6D2B79F5;
    t = Math.imul(t ^ t >>> 15, t | 1);
    t ^= t + Math.imul(t ^ t >>> 7, t | 61);
    return ((t ^ t >>> 14) >>> 0) / 4294967296;
  };
}
const rnd = mulberry32(20260518);
const pick = (arr) => arr[Math.floor(rnd() * arr.length)];
const range = (n) => Array.from({ length: n }, (_, i) => i);

// ---- formatters ------------------------------------------------------------
const formatUZS = (n) => {
  if (n == null) return '—';
  // UZS sums are big — show as compact unless < 100k
  if (n >= 1_000_000_000) return `${(n / 1_000_000_000).toFixed(2)}B UZS`;
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M UZS`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(0)}K UZS`;
  return `${n.toLocaleString()} UZS`;
};
const formatNum = (n) => (n ?? 0).toLocaleString();
const formatMs = (ms) => {
  if (ms == null) return '—';
  if (ms < 1000) return `${Math.round(ms)} ms`;
  return `${(ms / 1000).toFixed(1)} s`;
};
const formatDate = (d, opts = {}) => {
  const date = d instanceof Date ? d : new Date(d);
  const o = { month: 'short', day: 'numeric', year: 'numeric', ...opts };
  return date.toLocaleDateString('en-US', o);
};
const formatDateShort = (d) => {
  const date = d instanceof Date ? d : new Date(d);
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
};
const formatRelative = (d) => {
  const date = d instanceof Date ? d : new Date(d);
  const diff = (Date.now() - date.getTime()) / 1000;
  if (diff < 60) return 'just now';
  if (diff < 3600) return `${Math.floor(diff / 60)} min ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)} h ago`;
  if (diff < 86400 * 7) return `${Math.floor(diff / 86400)} d ago`;
  return formatDateShort(date);
};

// ---- name pools (UZ/RU realism) -------------------------------------------
const firstNames = [
  'Aziza', 'Bekzod', 'Dilshod', 'Elnura', 'Farrukh', 'Gulnora', 'Hasan', 'Iroda',
  'Jakhongir', 'Kamola', 'Laziz', 'Madina', 'Nodir', 'Oybek', 'Parvina', 'Qodir',
  'Rustam', 'Sevara', 'Temur', 'Umida', 'Vali', 'Xurshid', 'Yulduz', 'Zafar',
  'Anvar', 'Bahodir', 'Charos', 'Dilnoza', 'Eldor', 'Feruza', 'Anastasia', 'Dmitri',
  'Sergey', 'Olga', 'Mikhail', 'Tatiana', 'Aleksandr', 'Ekaterina',
];
const lastNames = [
  'Karimov', 'Yusupov', 'Tursunov', 'Mirzayev', 'Nazarov', 'Saidov', 'Rashidova', 'Ergasheva',
  'Akhmedova', 'Toshpulatov', 'Ismoilov', 'Kasimov', 'Petrov', 'Ivanov', 'Volkova', 'Sokolova',
];
const usernamePool = [
  'azizak', 'bekzodbek', 'dilshod_t', 'elnur404', 'farruk.h', 'gulnora_92', 'hasan.uz', 'iroda_quizz',
  'jh_tashkent', 'kamola_official', 'laz1z', 'madinadev', 'nodir_x', 'oybekt', 'parvina99', 'rustamio',
  'sevarka', 'temur_quiz', 'umida_a', 'vali_z', 'xurshid_99', 'yulduz_y', 'zafar.k', 'anvar_admin',
  'kuzya', 'sokolova_o', 'mishakod', 'dmtr', 'eka.t',
];

// ---- USERS -----------------------------------------------------------------
function makeUsers(n) {
  return range(n).map((i) => {
    const first = firstNames[Math.floor(rnd() * firstNames.length)];
    const last = lastNames[Math.floor(rnd() * lastNames.length)];
    const has_username = rnd() > 0.18;
    const username = has_username ? usernamePool[Math.floor(rnd() * usernamePool.length)] + (rnd() > 0.7 ? Math.floor(rnd() * 99) : '') : null;
    const lang = pick(['uz', 'uz', 'uz', 'ru', 'ru', 'en']);
    const created = new Date(Date.now() - Math.floor(rnd() * 220) * 86400 * 1000);
    const last_active = new Date(Date.now() - Math.floor(rnd() * 14) * 86400 * 1000 - Math.floor(rnd() * 86400 * 1000));
    const is_blocked = rnd() < 0.05;
    const has_sub = rnd() < 0.27;
    return {
      id: 100000 + i + 1,
      telegram_id: 100000000 + Math.floor(rnd() * 900000000),
      username,
      first_name: first,
      last_name: rnd() > 0.4 ? last : null,
      language_code: lang,
      created_at: created.toISOString(),
      last_active_at: last_active.toISOString(),
      is_blocked,
      quiz_count: is_blocked ? 0 : Math.floor(rnd() * 38),
      subscription: has_sub ? {
        plan: pick(['monthly', 'quarterly', 'yearly']),
        status: 'active',
        expires_at: new Date(Date.now() + Math.floor(rnd() * 90 + 5) * 86400 * 1000).toISOString(),
      } : null,
      total_paid_uzs: has_sub ? Math.floor(rnd() * 12 + 1) * 49000 : 0,
    };
  });
}
const USERS = makeUsers(127);

// ---- QUIZZES ---------------------------------------------------------------
const quizTitles = [
  'Tarix imtihoni 9-sinf', 'Ona tili: morfologiya', 'World Capitals Mega Pack', 'IELTS Vocabulary B2',
  'Математика: дроби', 'Algebra basics', 'Anatomy 101', 'Onomatopoeia in literature', 'Java Spring quick check',
  'JavaScript fundamentals', 'Geografiya — okeanlar', 'История России XIX век', 'Adabiyot: Cho‘lpon',
  'Test po fizike: optika', 'C++ pointers', 'React hooks deep dive', 'Eng. — Phrasal verbs vol. 2',
  'Biologiya: hujayra', 'PDD билеты 2026', 'O‘zbekistonning hududlari', 'Marketing 101', 'TOEFL writing prep',
  'Excel formulalar', 'Linear Algebra eigenvalues', 'Discrete math practice', 'Microbiology midterm',
  'Korean basics: Hangul', 'Turkcha boshlang‘ich', 'Civics test US', 'Chemistry: organic 2', 'SQL joins',
];
function makeQuizzes(n) {
  return range(n).map((i) => {
    const title = quizTitles[i % quizTitles.length] + (i >= quizTitles.length ? ` v${Math.ceil(i / quizTitles.length) + 1}` : '');
    const owner = USERS[Math.floor(rnd() * USERS.length)];
    const visibility = rnd() > 0.55 ? 'public' : 'private';
    const source_type = pick(['manual', 'manual', 'ai_pdf', 'ai_pdf', 'ai_docx', 'ai_image', 'duplicated']);
    return {
      id: 50000 + i + 1,
      title,
      owner_id: owner.id,
      owner_username: owner.username || `id${owner.telegram_id}`,
      questions_count: 5 + Math.floor(rnd() * 60),
      play_count: Math.floor(rnd() * rnd() * 4800),
      visibility,
      source_type,
      created_at: new Date(Date.now() - Math.floor(rnd() * 140) * 86400 * 1000).toISOString(),
      deleted_at: rnd() < 0.04 ? new Date().toISOString() : null,
    };
  });
}
const QUIZZES = makeQuizzes(86);

// ---- IMPORT LOGS -----------------------------------------------------------
function makeImportLogs(n) {
  return range(n).map((i) => {
    const status = pick(['completed', 'completed', 'completed', 'completed', 'failed', 'pending']);
    const file_type = pick(['pdf', 'pdf', 'docx', 'image', 'txt']);
    const file_name = `${pick(['Tarix', 'Math', 'Biology', 'Algebra', 'IELTS_unit', 'Hujayra_test', 'PDD_bilet', 'JS_basics', 'React_intro', 'TOEFL_prep'])}_${Math.floor(rnd() * 99) + 1}.${file_type === 'image' ? 'png' : file_type}`;
    return {
      id: 9000 + i + 1,
      file_name,
      file_type,
      status,
      total_imported: status === 'completed' ? 8 + Math.floor(rnd() * 42) : 0,
      processing_time_ms: status === 'pending' ? null : Math.floor(800 + rnd() * 14000),
      user_id: USERS[Math.floor(rnd() * USERS.length)].id,
      created_at: new Date(Date.now() - Math.floor(rnd() * 30) * 86400 * 1000 - Math.floor(rnd() * 86400 * 1000)).toISOString(),
      error: status === 'failed' ? pick(['Unable to detect questions', 'OCR confidence too low', 'File too large', 'Rate limit exceeded']) : null,
    };
  });
}
const IMPORT_LOGS = makeImportLogs(64);

// ---- ANALYTICS -------------------------------------------------------------
function makeGrowth(days) {
  let users = 880;
  let quizzes = 320;
  return range(days).map((i) => {
    const day = new Date(Date.now() - (days - 1 - i) * 86400 * 1000);
    const dayOfWeek = day.getDay();
    const weekendBoost = (dayOfWeek === 0 || dayOfWeek === 6) ? 1.18 : 1;
    const newUsers = Math.max(2, Math.floor((6 + rnd() * 22) * weekendBoost));
    const newQuizzes = Math.max(1, Math.floor((3 + rnd() * 14) * weekendBoost));
    users += newUsers;
    quizzes += newQuizzes;
    return {
      date: day.toISOString().slice(0, 10),
      new_users: newUsers,
      new_quizzes: newQuizzes,
      total_users: users,
      total_quizzes: quizzes,
    };
  });
}
const GROWTH_30 = makeGrowth(30);

function makeRevenue(days) {
  return range(days).map((i) => {
    const day = new Date(Date.now() - (days - 1 - i) * 86400 * 1000);
    const count = Math.floor(rnd() * 14) + (i % 7 === 0 ? 3 : 0);
    const amount = count * (49000 + Math.floor(rnd() * 100000));
    return {
      date: day.toISOString().slice(0, 10),
      amount_uzs: amount,
      count,
      provider: pick(['click', 'payme', 'uzcard']),
    };
  });
}
const REVENUE_30 = makeRevenue(30);

const OVERVIEW = {
  users: {
    total: USERS.length + 1340,
    new_today: 47,
    new_this_week: 318,
    active_this_week: 612,
    blocked: USERS.filter(u => u.is_blocked).length + 12,
  },
  quizzes: {
    total: QUIZZES.length + 740,
    public: QUIZZES.filter(q => q.visibility === 'public').length + 412,
    private: QUIZZES.filter(q => q.visibility === 'private').length + 328,
    new_this_week: 89,
  },
  subscriptions: {
    active: USERS.filter(u => u.subscription).length + 184,
  },
  revenue: {
    total_uzs: 48_750_000,
    this_month_uzs: 7_290_000,
  },
};

const IMPORT_BREAKDOWN = [
  { status: 'completed', file_type: 'pdf', count: 218, avg_processing_ms: 4200, avg_questions: 24 },
  { status: 'completed', file_type: 'docx', count: 84, avg_processing_ms: 2900, avg_questions: 18 },
  { status: 'completed', file_type: 'image', count: 41, avg_processing_ms: 7600, avg_questions: 12 },
  { status: 'failed', file_type: 'pdf', count: 19, avg_processing_ms: 6100, avg_questions: 0 },
  { status: 'failed', file_type: 'image', count: 11, avg_processing_ms: 8400, avg_questions: 0 },
  { status: 'pending', file_type: 'pdf', count: 3, avg_processing_ms: null, avg_questions: null },
];

// ---- NOTIFICATIONS ---------------------------------------------------------
const TEMPLATES = [
  { slug: 'quiz_ready', name: 'Quiz ready', description: 'Sent when an AI-imported quiz is ready to play.', is_active: true,
    text_uz: '✅ Quizingiz tayyor! "{quiz_title}" — {questions} ta savol.',
    text_ru: '✅ Ваш тест готов! «{quiz_title}» — {questions} вопросов.',
    text_en: '✅ Your quiz is ready! "{quiz_title}" — {questions} questions.' },
  { slug: 'daily_reminder', name: 'Daily reminder', description: 'Reminder for users who haven’t played in 24h.', is_active: true,
    text_uz: '👋 {first_name}, bugun bir quiz ishlab qo‘ying!',
    text_ru: '👋 {first_name}, реши хотя бы один тест сегодня!',
    text_en: '👋 {first_name}, solve at least one quiz today!' },
  { slug: 'subscription_expiring', name: 'Subscription expiring', description: 'Sent 3 days before subscription ends.', is_active: true,
    text_uz: '⚠️ Obunangiz {days} kun ichida tugaydi.',
    text_ru: '⚠️ Ваша подписка истекает через {days} дн.',
    text_en: '⚠️ Your subscription expires in {days} days.' },
  { slug: 'import_failed', name: 'Import failed', description: 'Sent when AI import fails.', is_active: true,
    text_uz: '❌ "{file_name}" faylini qayta ishlay olmadik. Sabab: {reason}',
    text_ru: '❌ Не удалось обработать «{file_name}». Причина: {reason}',
    text_en: '❌ We couldn’t process "{file_name}". Reason: {reason}' },
  { slug: 'welcome', name: 'Welcome message', description: 'First message on /start.', is_active: true,
    text_uz: 'Quizly’ga xush kelibsiz, {first_name}! 🎉',
    text_ru: 'Добро пожаловать в Quizly, {first_name}! 🎉',
    text_en: 'Welcome to Quizly, {first_name}! 🎉' },
  { slug: 'payment_success', name: 'Payment success', description: 'Confirmation after successful payment.', is_active: false,
    text_uz: '💳 To‘lov qabul qilindi. Rahmat!',
    text_ru: '💳 Платёж получен. Спасибо!',
    text_en: '💳 Payment received. Thank you!' },
];

const NOTIFICATIONS = range(28).map((i) => {
  const created = new Date(Date.now() - i * 86400 * 1000 - Math.floor(rnd() * 86400 * 1000));
  const recipients = 80 + Math.floor(rnd() * 1800);
  const failed = Math.floor(recipients * (0.005 + rnd() * 0.04));
  return {
    id: 7000 + i,
    text: pick([
      'Yangi yangilanish: AI import endi rasm fayllarini ham qo‘llab-quvvatlaydi 🚀',
      'Праздничная акция: подписка на 30% дешевле до конца недели!',
      'New feature: leaderboards are now available for public quizzes.',
      'Texnik ish: bugun 03:00 dan 04:00 gacha bot ishlamasligi mumkin.',
      'Promo: подари другу подписку и получи 1 месяц бесплатно.',
    ]),
    language_code: pick(['all', 'uz', 'ru', 'en']),
    recipients,
    delivered: recipients - failed,
    failed,
    status: i === 0 ? 'sending' : 'completed',
    created_at: created.toISOString(),
    sent_by: pick(['admin@quizly', 'farrukh.k', 'system']),
  };
});

// ---- SETTINGS / ADMINS -----------------------------------------------------
const SETTINGS = {
  maintenance_mode:        { value: 'false', description: 'When true, the bot replies only with a maintenance notice.' },
  max_file_size_mb:        { value: '20',    description: 'Max upload size for AI import.' },
  default_set_size:        { value: '10',    description: 'Default number of questions per practice set.' },
  ai_provider:             { value: 'gpt-4o-mini', description: 'Model used for question extraction.' },
  free_imports_per_day:    { value: '3',     description: 'Free AI imports allowed per non-subscriber per day.' },
  monthly_price_uzs:       { value: '49000', description: 'Price of the monthly subscription, in UZS.' },
  quarterly_price_uzs:     { value: '129000',description: 'Price of the 3-month subscription, in UZS.' },
  yearly_price_uzs:        { value: '449000',description: 'Price of the 12-month subscription, in UZS.' },
  support_username:        { value: '@quizly_support', description: 'Telegram username shown in the help menu.' },
  broadcast_rate_per_sec:  { value: '25',    description: 'Telegram API rate limit for broadcast jobs.' },
};

const ADMINS = [
  { id: 1, telegram_id: 312_445_001, username: 'farrukh_admin',  role: 'owner',  created_at: '2025-08-12T09:00:00Z' },
  { id: 2, telegram_id: 412_990_222, username: 'aziza_pm',       role: 'admin',  created_at: '2025-11-04T11:20:00Z' },
  { id: 3, telegram_id: 580_211_500, username: 'temur.support',  role: 'support',created_at: '2026-01-18T14:05:00Z' },
  { id: 4, telegram_id: 690_440_711, username: 'mikhail_ops',    role: 'admin',  created_at: '2026-02-22T08:32:00Z' },
];

// ---- Store -----------------------------------------------------------------
// Lightweight reactive store using useSyncExternalStore.
function createStore(initial) {
  let state = initial;
  const listeners = new Set();
  return {
    get: () => state,
    set: (updater) => {
      state = typeof updater === 'function' ? updater(state) : updater;
      listeners.forEach(l => l());
    },
    subscribe: (l) => { listeners.add(l); return () => listeners.delete(l); },
  };
}

const store = createStore({
  users: USERS,
  quizzes: QUIZZES,
  importLogs: IMPORT_LOGS,
  notifications: NOTIFICATIONS,
  templates: TEMPLATES,
  settings: SETTINGS,
  admins: ADMINS,
  overview: OVERVIEW,
  growth30: GROWTH_30,
  revenue30: REVENUE_30,
  importBreakdown: IMPORT_BREAKDOWN,
});

const useStore = (selector = (s) => s) =>
  React.useSyncExternalStore(store.subscribe, () => selector(store.get()));

Object.assign(window, {
  store, useStore,
  formatUZS, formatNum, formatMs, formatDate, formatDateShort, formatRelative,
});
