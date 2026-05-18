# Quiz Bot — QA (Quality Assurance)

## 1. Test Turlari

```
┌───────────────────────────────────────────────────────┐
│ Test Piramidasi                                       │
│                                                       │
│          /\        E2E Tests (10%)                    │
│         /  \       — to'liq oqimlarni tekshirish     │
│        /────\                                        │
│       /      \     Integration Tests (30%)           │
│      /        \    — xizmatlar orasini tekshirish    │
│     /──────────\                                     │
│    /            \   Unit Tests (60%)                  │
│   /              \  — alohida funksiyalarni tekshirish│
│  /────────────────\                                  │
└───────────────────────────────────────────────────────┘
```

---

## 2. Unit Tests

### Go xizmatlari (gateway, game, notifier)

```
Tool: go test + testify
Coverage: minimum 80%

Nima test qilinadi:
├── Score hisoblash logikasi
├── Leaderboard ranking algoritmi
├── Webhook routing
├── Notification template rendering
├── Input validation
└── Edge cases (bo'sh array, null, overflow)
```

### Python xizmatlari (bot, ai-engine, admin-api, subscription)

```
Tool: pytest + pytest-asyncio
Coverage: minimum 80%

Nima test qilinadi:
├── AI parser — har bir format uchun (word, pdf, excel, image, txt)
├── Boundary detection — savol/variant ajratish
├── Validation — AI natijasini tekshirish
├── Subscription limit — to'g'ri hisoblanishi
├── XP hisoblash — to'g'ri berilishi
├── State machine — holatlar orasida to'g'ri o'tish
└── Edge cases
```

### Misol test lar

```python
# ai-engine: boundary detection test
def test_boundary_detects_numbered_questions():
    text = "1. Savol bir\nA) variant\nB) variant\n2. Savol ikki\nA) variant"
    blocks = detect_boundaries(text)
    assert len(blocks) == 2
    assert blocks[0].question == "Savol bir"
    assert len(blocks[0].options) == 2

def test_boundary_handles_empty_text():
    blocks = detect_boundaries("")
    assert blocks == []

# game: XP hisoblash test
def test_xp_for_perfect_score():
    xp = calculate_xp(correct=20, total=20, streak_days=5)
    assert xp == 10 + 25 + (5 * 5)  # base + perfect + streak

def test_xp_no_negative():
    xp = calculate_xp(correct=0, total=20, streak_days=0)
    assert xp >= 0
```

---

## 3. Integration Tests

```
Tool: pytest + docker-compose (test environment)
Database: test PostgreSQL (har test dan keyin truncate)

Nima test qilinadi:
├── Bot → AI Engine: fayl yuklash → quiz yaratilish
├── Bot → Subscription: limit tekshirish oqimi
├── Bot → Game: quiz boshlash → javob berish → natija
├── Game → Leaderboard: score yangilanishi
├── AI Engine → DB: quiz va questions to'g'ri yozilishi
├── Subscription → Payment: to'lov oqimi
└── Notifier → Redis Queue: xabar ketish
```

### Integration test qoidalari

```
✅ QILISH:
├── Har bir xizmat juftligi uchun kamida 1 integration test
├── Real PostgreSQL va Redis ishlatish (mock emas)
├── Test ma'lumotlarini har testda yangilash
├── Timeout lar qo'yish (5 sekund max)
└── Error case larni ham test qilish

❌ QILMASLIK:
├── External API (OpenAI, Telegram) ni real chaqirish
├── Production database ga ulanish
├── Test lar orasida holatni saqlash (har biri mustaqil)
└── Sekin testlar yozish (30 sek dan oshmasin)
```

---

## 4. E2E Tests

```
Tool: pytest + Telegram test account (yoki mock server)

To'liq oqimlar:
├── Onboarding: /start → til tanlash → menyu
├── Quiz o'ynash: boshlash → javob → natija
├── Fayl yuklash: fayl → AI → quiz tayyor
├── Pause/Stop: 2x skip → pauza → davom
├── Xatolarni qayta ishlash: noto'g'ri → retry → tuzatish
├── Premium: limit → paywall → to'lov → limit ochilishi
├── Referal: link → ro'yxat → bonus
├── Quiz Guruh: yaratish → quiz biriktirish → obuna → xabar
└── Telegram guruh: voting → quiz → natija
```

---

## 5. AI Engine Maxsus Testlar

```
AI pipeline har bir stage uchun alohida test:

Stage 1 (Format Detect):
├── .docx → word_parser tanlanishi
├── .pdf → pdf_parser tanlanishi
├── Noma'lum format → xato qaytarilishi

Stage 2 (Extraction):
├── Test Word fayl → to'g'ri matn chiqishi
├── Test PDF (jadval bilan) → jadval saqlanishi
├── Test Excel → row/column to'g'ri o'qilishi
├── Test rasm → Vision API chaqirilishi (mock)

Stage 3 (Boundary):
├── Raqamli savollar (1. 2. 3.) → to'g'ri ajratilishi
├── Harfli variantlar (A B C D) → to'g'ri topilishi
├── To'g'ri javob belgisi (*, qalin) → aniqlanishi
├── Aralash format → eng yaxshi natija

Stage 4 (AI Structuring):
├── Mock AI response → to'g'ri JSON parse
├── Noto'g'ri AI response → retry ishga tushishi
├── Batch (10 savol) → barcha parse bo'lishi

Stage 5 (Validation):
├── To'g'ri JSON → approve
├── Yo'qolgan variant → fail + retry
├── Dublikat savol → olib tashlash
├── correct_index chegaradan tashqari → fail

Test fayllar:
services/ai-engine/tests/fixtures/
├── sample_biology.docx      (100 savol, oddiy)
├── sample_with_tables.pdf   (jadval bilan)
├── sample_mixed.pdf         (matn + rasm)
├── sample_simple.xlsx       (column = savol/A/B/C/D/javob)
├── sample_screenshot.png    (skan)
├── sample_broken.docx       (buzilgan format)
└── sample_no_answers.txt    (javobsiz)
```

---

## 6. Performance Tests

```
Tool: locust (Python) yoki k6 (Go)

Nima test qilinadi:
├── Gateway: 10,000 webhook/sekund
├── Game: 5,000 concurrent quiz sessions
├── Bot: 1,000 simultaneous file uploads
├── DB: 100,000 answers/minute yozish
└── Redis: 50,000 cache read/sekund

Maqsadli ko'rsatkichlar (SLA):
├── Gateway response: < 50ms (p95)
├── Quiz poll yuborish: < 200ms
├── AI processing (10 savol): < 5 sekund
├── Leaderboard so'rov: < 100ms
└── Notification yuborish: < 500ms
```

---

## 7. Test Environment

```
docker-compose.test.yml:

services:
  postgres-test:
    image: postgres:16
    environment:
      POSTGRES_DB: quiz_bot_test
    tmpfs: /var/lib/postgresql/data  ← RAM da (tez)

  redis-test:
    image: redis:7
    
  ai-engine-test:
    build: ./services/ai-engine
    environment:
      OPENAI_API_KEY: "sk-test-mock"  ← mock
      DATABASE_URL: postgres-test

  game-test:
    build: ./services/game
    environment:
      DATABASE_URL: postgres-test
```

---

## 8. CI Pipeline da Test Ketma-ketligi

```
PR ochilganda:

1. Lint + Format tekshirish
   ├── Go: golangci-lint
   ├── Python: ruff + black
   └── FAIL → PR merge bo'lmaydi

2. Unit Tests
   ├── Go: go test ./...
   ├── Python: pytest tests/unit/
   └── Coverage < 80% → FAIL

3. Integration Tests
   ├── Docker compose up (test env)
   ├── pytest tests/integration/
   └── Docker compose down

4. E2E Tests (faqat main ga merge da)
   ├── Full environment deploy (staging)
   ├── pytest tests/e2e/
   └── Cleanup

5. Performance Tests (haftada 1 marta yoki manual)
   ├── k6/locust run
   └── Report
```

---

## 9. Monitoring va Alerting (Production)

```
Tool: Prometheus + Grafana

Metrikalar:
├── request_duration_seconds (gateway)
├── active_games_total (game)
├── ai_processing_duration_seconds (ai-engine)
├── poll_send_success_rate (bot)
├── payment_success_rate (subscription)
├── notification_delivery_rate (notifier)
└── error_rate_per_service

Alertlar:
├── Error rate > 5% → Telegram admin guruhga xabar
├── AI processing > 30 sek → tekshir
├── Payment fail rate > 10% → darhol tekshir
├── DB connection pool 80%+ → scale up
└── Redis memory 80%+ → cache TTL kamaytir
```

---

## 10. Bug Report Format

```
Har bir bug uchun:

Sarlavha: [Xizmat] Qisqa tavsif
Muhimlik: Critical / High / Medium / Low
Qayta yaratish:
1. Qadam 1
2. Qadam 2
3. ...
Kutilgan natija: ...
Haqiqiy natija: ...
Screenshot/Log: ...
Environment: production / staging / local
```

---

## 11. Release Checklist

```
Har bir release dan oldin:

□ Barcha unit testlar o'tdi
□ Integration testlar o'tdi
□ E2E testlar (staging da) o'tdi
□ DB migration to'g'ri ishlaydi (up/down)
□ .env.example yangilangan
□ ARCHITECTURE.md yangilangan (kerak bo'lsa)
□ Rollback rejasi tayyor
□ Monitoring dashboard tekshirildi
```
