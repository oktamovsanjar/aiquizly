// Real API integration + lightweight reactive store.
// Mock data is kept only as fallback / initial state while API loads.

// ---- formatters ------------------------------------------------------------
const formatUZS = (n) => {
  if (n == null) return '—';
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
  if (!d) return '—';
  const date = d instanceof Date ? d : new Date(d);
  const o = { month: 'short', day: 'numeric', year: 'numeric', ...opts };
  return date.toLocaleDateString('en-US', o);
};
const formatDateShort = (d) => {
  if (!d) return '—';
  const date = d instanceof Date ? d : new Date(d);
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
};
const formatRelative = (d) => {
  if (!d) return '—';
  const date = d instanceof Date ? d : new Date(d);
  const diff = (Date.now() - date.getTime()) / 1000;
  if (diff < 60) return 'just now';
  if (diff < 3600) return `${Math.floor(diff / 60)} min ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)} h ago`;
  if (diff < 86400 * 7) return `${Math.floor(diff / 86400)} d ago`;
  return formatDateShort(date);
};

// ---- Notification templates (static, no API) --------------------------------
const TEMPLATES = [
  { slug: 'quiz_ready', name: 'Quiz ready', description: 'Sent when an AI-imported quiz is ready to play.', is_active: true,
    text_uz: '✅ Quizingiz tayyor! "{quiz_title}" — {questions} ta savol.',
    text_ru: '✅ Ваш тест готов! «{quiz_title}» — {questions} вопросов.',
    text_en: '✅ Your quiz is ready! "{quiz_title}" — {questions} questions.' },
  { slug: 'daily_reminder', name: 'Daily reminder', description: 'Reminder for users who haven't played in 24h.', is_active: true,
    text_uz: '👋 {first_name}, bugun bir quiz ishlab qo'ying!',
    text_ru: '👋 {first_name}, реши хотя бы один тест сегодня!',
    text_en: '👋 {first_name}, solve at least one quiz today!' },
  { slug: 'subscription_expiring', name: 'Subscription expiring', description: 'Sent 3 days before subscription ends.', is_active: true,
    text_uz: '⚠️ Obunangiz {days} kun ichida tugaydi.',
    text_ru: '⚠️ Ваша подписка истекает через {days} дн.',
    text_en: '⚠️ Your subscription expires in {days} days.' },
  { slug: 'import_failed', name: 'Import failed', description: 'Sent when AI import fails.', is_active: true,
    text_uz: '❌ "{file_name}" faylini qayta ishlay olmadik. Sabab: {reason}',
    text_ru: '❌ Не удалось обработать «{file_name}». Причина: {reason}',
    text_en: '❌ We couldn't process "{file_name}". Reason: {reason}' },
  { slug: 'welcome', name: 'Welcome message', description: 'First message on /start.', is_active: true,
    text_uz: 'Quizly'ga xush kelibsiz, {first_name}! 🎉',
    text_ru: 'Добро пожаловать в Quizly, {first_name}! 🎉',
    text_en: 'Welcome to Quizly, {first_name}! 🎉' },
  { slug: 'payment_success', name: 'Payment success', description: 'Confirmation after successful payment.', is_active: false,
    text_uz: '💳 To'lov qabul qilindi. Rahmat!',
    text_ru: '💳 Платёж получен. Спасибо!',
    text_en: '💳 Payment received. Thank you!' },
];

// ---- Initial empty state ---------------------------------------------------
const EMPTY_OVERVIEW = {
  users: { total: 0, new_today: 0, new_this_week: 0, active_this_week: 0, blocked: 0 },
  quizzes: { total: 0, public: 0, private: 0, new_this_week: 0 },
  subscriptions: { active: 0 },
  revenue: { total_uzs: 0, this_month_uzs: 0 },
};

// ---- Store -----------------------------------------------------------------
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
  users: [],
  quizzes: [],
  importLogs: [],
  notifications: [],
  templates: TEMPLATES,
  settings: {},
  admins: [],
  overview: EMPTY_OVERVIEW,
  growth30: [],
  revenue30: [],
  importBreakdown: [],
  _loading: false,
  _loaded: false,
  _error: null,
});

const useStore = (selector = (s) => s) =>
  React.useSyncExternalStore(store.subscribe, () => selector(store.get()));

// ---- Real API ---------------------------------------------------------------
const API_BASE = window.location.origin + '/admin';

async function apiFetch(path, options = {}) {
  const token = localStorage.getItem('admin_token') || '';
  const res = await fetch(API_BASE + path, {
    ...options,
    headers: {
      'X-Admin-Token': token,
      'Content-Type': 'application/json',
      ...(options.headers || {}),
    },
  });
  if (!res.ok) throw new Error(`${res.status} ${path}`);
  return res.json();
}

async function loadRealData() {
  if (store.get()._loading || store.get()._loaded) return;
  store.set(s => ({ ...s, _loading: true, _error: null }));
  try {
    const [overview, growth, imports, settings, admins] = await Promise.allSettled([
      apiFetch('/analytics/overview'),
      apiFetch('/analytics/growth?days=30'),
      apiFetch('/analytics/imports'),
      apiFetch('/settings'),
      apiFetch('/admins'),
    ]);

    const updates = {};

    if (overview.status === 'fulfilled') {
      updates.overview = overview.value;
    }

    if (growth.status === 'fulfilled' && growth.value.data) {
      updates.growth30 = growth.value.data.map(d => ({
        date: d.date,
        new_users: d.new_users || 0,
        new_quizzes: d.new_quizzes || 0,
      }));
    }

    if (imports.status === 'fulfilled') {
      updates.importBreakdown = imports.value.breakdown || [];
    }

    if (settings.status === 'fulfilled') {
      updates.settings = settings.value;
    }

    if (admins.status === 'fulfilled') {
      updates.admins = admins.value.admins || admins.value || [];
    }

    store.set(s => ({ ...s, ...updates, _loading: false, _loaded: true }));
  } catch (e) {
    store.set(s => ({ ...s, _loading: false, _error: e.message }));
  }
}

Object.assign(window, {
  store, useStore, loadRealData, apiFetch,
  formatUZS, formatNum, formatMs, formatDate, formatDateShort, formatRelative,
});
