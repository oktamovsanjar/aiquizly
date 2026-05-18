# Quiz Bot — Arxitektura Qoidalari

## 1. Xizmatlar va Tillar

### GO yoziladigan xizmatlar

| Xizmat | Vazifa | Sabab |
|---|---|---|
| `gateway` | Telegram webhook qabul qilish, routerlash | Million request, past latency |
| `game` | Score hisoblash, real-time leaderboard | Concurrency, tez hisob |
| `notifier` | Push notification, mass xabar yuborish | Parallellik, tezlik |

### PYTHON yoziladigan xizmatlar

| Xizmat | Vazifa | Sabab |
|---|---|---|
| `bot` | Telegram bot logikasi (aiogram) | aiogram faqat Python |
| `ai-engine` | Fayl parsing, OpenAI, quiz generatsiya | AI kutubxonalar faqat Python |
| `admin-api` | Admin panel backend (FastAPI) | Tez ishlab chiqish |

---

## 2. Qat'iy Qoidalar

### Nima MUMKIN

```
✅ Go xizmat → Python xizmatga HTTP yoki gRPC orqali murojaat qilish
✅ Python xizmat → Go xizmatga HTTP yoki gRPC orqali murojaat qilish
✅ Istalgan xizmat → Redis Queue orqali task yuborish
✅ Istalgan xizmat → PostgreSQL dan o'qish/yozish (o'z modellari orqali)
✅ Har bir xizmatning o'z config fayli bo'lishi
✅ Har bir xizmatning o'z Dockerfile bo'lishi
```

### Nima MUMKIN EMAS

```
❌ Bir xizmat ichida Go + Python aralash yozish
❌ Xizmatlar bir-birining database jadvallariga to'g'ridan murojaat qilishi
❌ Bot ichida AI kodni yozish (ai-engine alohida xizmat)
❌ Go da aiogram yoki Telegram bot logikasi yozish
❌ Python da WebSocket million user uchun (Go notifier ishlatiladi)
❌ Database orqali xizmatlar orasida muloqot (shared DB anti-pattern)
❌ Hardcode qilingan config (token, key, URL) — faqat .env
❌ Bir xizmatdan boshqa xizmatning internal funksiyasini chaqirish
```

---

## 3. Xizmatlar Orasida Muloqot

```
Qoida: 2 ta usul bor, boshqasi yo'q.

1. HTTP REST yoki gRPC  → sinxron (javob kutilsa)
2. Redis Queue (Celery) → asinxron (AI task, notification)
```

### Misol — To'g'ri

```
Bot (Python) --[Redis Queue]--> AI Engine (Python)
AI Engine    --[HTTP POST]----> Admin API (Python)
Gateway (Go) --[gRPC]---------> Game (Go)
Game (Go)    --[Redis Queue]--> Notifier (Go)
```

### Misol — Noto'g'ri

```
❌ Bot (Python) → DB ni to'g'ridan o'qib Game natijasini hisoblash
❌ Gateway (Go) → AI Engine kodini import qilish
❌ Admin API → Bot xizmatining ichki funksiyasini chaqirish
```

---

## 4. Daromad Modeli va Obuna Tizimi

### Tariflar

```
FREE
├── Oyiga 3 ta fayl yuklash
├── Har bir fayldan max 50 savol
├── Quiz faqat o'zi uchun (private)
└── Quiz 7 kun saqlangach o'chadi

PREMIUM (oylik / yillik)
├── Cheksiz fayl yuklash
├── Cheksiz savol
├── Guruhga ulashish
├── Quiz doim saqlanadi
├── Batafsil statistika
└── O'z nomi bilan branding

BUSINESS (maktab, kurs markaz)
├── Premium + hammasi
├── Bir nechta admin
├── O'z bot tokeni (white-label)
├── Natijalarni Excel eksport
└── API access
```

### To'lov Usullari

```
Telegram Stars  ← asosiy (Telegram native, eng oson)
Payme / Click   ← O'zbekiston foydalanuvchilari uchun
Stripe          ← xalqaro foydalanuvchilar uchun
```

### Limit Tekshirish Qoidasi

```
Har bir fayl yuklash so'rovida:
  bot middleware → subscription servisga so'rov
                → limit oshganmi?
                   → HA: premium taklif xabari
                   → YO'Q: AI Engine ga yuvor

Limit tekshiruvi FAQAT bot middleware da bo'ladi.
Boshqa joylarda limit tekshirish MUMKIN EMAS.
```

---

## 5. Database Qoidalari

```
PostgreSQL — asosiy ma'lumotlar
Redis      — cache, session, queue

Har bir xizmat FAQAT o'z jadvallariga yozadi:
┌─────────────┬───────────────────────────────────────────────────────────┐
│ Xizmat      │ Jadvallar                                                 │
├─────────────┼───────────────────────────────────────────────────────────┤
│ bot         │ users, quiz_groups, quiz_group_subscribers,               │
│             │ referrals, telegram_groups                                │
├─────────────┼───────────────────────────────────────────────────────────┤
│ subscription│ plans, subscriptions, payments, usage_logs                │
├─────────────┼───────────────────────────────────────────────────────────┤
│ ai-engine   │ tags, quizzes, quiz_tags, quiz_sets, questions,           │
│             │ import_logs                                               │
├─────────────┼───────────────────────────────────────────────────────────┤
│ game        │ games, answers, user_stats, xp_logs, achievements,       │
│             │ user_achievements, leaderboards                           │
├─────────────┼───────────────────────────────────────────────────────────┤
│ notifier    │ notification_templates, notifications                     │
├─────────────┼───────────────────────────────────────────────────────────┤
│ admin-api   │ admins, settings                                          │
└─────────────┴───────────────────────────────────────────────────────────┘

Boshqa jadvaldan ma'lumot kerak bo'lsa → HTTP API orqali so'ra.
```

---

## 6. Papka Strukturasi

```
quiz-bot/
├── services/
│   ├── gateway/           ← GO
│   │   ├── main.go
│   │   ├── handlers/
│   │   ├── router/
│   │   └── Dockerfile
│   │
│   ├── game/              ← GO
│   │   ├── main.go
│   │   ├── scoring/
│   │   ├── leaderboard/
│   │   └── Dockerfile
│   │
│   ├── notifier/          ← GO
│   │   ├── main.go
│   │   ├── sender/
│   │   └── Dockerfile
│   │
│   ├── bot/               ← PYTHON
│   │   ├── main.py
│   │   ├── handlers/
│   │   ├── middlewares/
│   │   ├── keyboards/
│   │   ├── requirements.txt
│   │   └── Dockerfile
│   │
│   ├── ai-engine/         ← PYTHON
│   │   ├── main.py
│   │   ├── parsers/       ← PDF, Word, Excel, OCR
│   │   ├── openai/        ← GPT integration
│   │   ├── tasks/         ← Celery tasks
│   │   ├── requirements.txt
│   │   └── Dockerfile
│   │
│   ├── admin-api/         ← PYTHON
│   │   ├── main.py
│   │   ├── routers/
│   │   ├── models/
│   │   ├── requirements.txt
│   │   └── Dockerfile
│   │
│   └── subscription/      ← PYTHON
│       ├── main.py
│       ├── plans/         ← Tarif rejalari
│       ├── payments/      ← Telegram Stars, Payme, Stripe
│       ├── limits/        ← Limit tekshirish logikasi
│       ├── requirements.txt
│       └── Dockerfile
│
├── shared/
│   ├── proto/             ← gRPC schema (Go + Python uchun)
│   └── migrations/        ← DB migrations (Alembic)
│
├── infra/
│   ├── nginx/
│   ├── redis/
│   └── postgres/
│
├── docker-compose.yml
├── docker-compose.prod.yml
├── .env.example
└── ARCHITECTURE.md
```

---

## 7. AI Pipeline — Faylni Quizga Aylantirish

### Umumiy Oqim

```
FAYL → FORMAT DETECT → EXTRACTION → BOUNDARY DETECT → AI STRUCTURE → VERIFY → DB
```

### Stage 1: Format Detector

```
Fayl kelganda avval turini aniqla:

.docx  → Word Parser pipeline
.pdf   → PDF Parser pipeline
.xlsx  → Excel Parser pipeline (eng oson)
.png/.jpg → Vision pipeline
.txt   → Text Parser pipeline

Qoida: Har bir format uchun ALOHIDA parser.
       Universal parser QILMA — har doim buziladi.
```

### Stage 2: Raw Extraction (format bo'yicha)

```
WORD (.docx):
├── python-docx kutubxonasi
├── Paragraflar → matn sifatida
├── Jadvallar → ALOHIDA list of rows sifatida
├── Qalin/kursiv/rangni SAQLASH (to'g'ri javob belgisi bo'lishi mumkin)
└── Rasmlar → alohida ajratib saqlash

PDF:
├── PyMuPDF (fitz) — matn + KOORDINATALARI (x, y pozitsiya)
├── Jadvallar → camelot yoki tabula-py (maxsus jadval extractor)
├── Skanirlangan PDF → Vision pipeline ga o'tkazish
└── Aralash (matn + skan) → sahifani tekshir, kerak bo'lsa bo'l

EXCEL (.xlsx):
├── openpyxl
├── Struktura tayyor — column = savol/A/B/C/D/javob
├── Header qatorni aniqla, ma'lumotni o'qi
└── Bu format AI SIZ ham parse qilinadi (fallback)

IMAGE (.png/.jpg):
├── GPT-4 Vision — to'liq sahifani yubor (bo'laklama!)
├── 1 sahifa = 1 API call
├── Agar sahifa juda katta → gorizontal bo'shliqdan BO'L
└── Overlap: pastki 20% keyingi bo'lakka ham qo'shiladi

TEXT (.txt):
├── Encoding aniqlash (UTF-8, Windows-1251)
├── Line-by-line o'qish
└── Pattern-based boundary detection
```

### Stage 3: Boundary Detection (eng muhim qadam)

```
Maqsad: Har bir savolni variantlari bilan BITTA BLOK qilib ajratish.

Savol boshlanish belgilari:
├── Raqam + nuqta/qavs: "1." "1)" "№1"
├── Qalin shrift bilan boshlangan matn
└── Oldingi blokdan bo'sh qator/chiziq bilan ajralgan

Variant belgilari:
├── Harf + qavs: "A)" "a)" "A."
├── Harf + nuqta: "a." "b." "c." "d."
└── Belgi: "○" "●" "□" "■"

To'g'ri javob belgilari:
├── Qalin yoki rangli variant
├── "✓" yoki "*" belgisi
├── Alohida "Javob:" qatori
└── Excel da alohida "answer" columni

Qoida: BLOK = savol matni + barcha variantlar + (ixtiyoriy) javob
       Har bir blok keyingi stage ga ALOHIDA yuboriladi.
```

### Stage 4: AI Structuring (batch)

```
Qoida: AI ga 1ta savol emas, 10-15 savollik BATCH yuboriladi.
       Bu 10x tezroq va 10x arzonroq.

INPUT (AI ga yuboriladi):
───────────────────────────
Quyidagi savollarni JSON formatga o'tkaz.
Har bir savol uchun: question, options[], correct_index, explanation.

1. O'zbekiston qachon mustaqil bo'lgan?
A) 1990
B) 1991
C) 1992
D) 1993
Javob: B

2. Toshkent aholisi qancha?
...
───────────────────────────

OUTPUT (AI dan keladi):
───────────────────────────
[
  {
    "question": "O'zbekiston qachon mustaqil bo'lgan?",
    "options": ["1990", "1991", "1992", "1993"],
    "correct_index": 1,
    "explanation": "O'zbekiston 1991-yil 1-sentabrda mustaqillikka erishgan."
  },
  ...
]
───────────────────────────

AI modeli: GPT-4o-mini (arzon, tez, aniq)
Fallback: GPT-4o (agar mini xato qilsa)
```

### Stage 5: Validation va Verification

```
Har bir AI natijasi tekshiriladi:

MANDATORY CHECKS:
├── ✅ JSON format valid?
├── ✅ Har bir savolda kamida 2 variant bor?
├── ✅ correct_index variant soni ichida?
├── ✅ Savol matni bo'sh emas?
├── ✅ Dublikat savol yo'q? (fuzzy match)
└── ✅ Kutilgan soni == topilgan soni?

AGAR FAIL:
├── 1-urinish: shu blokni qayta AI ga yuborish (retry)
├── 2-urinish: blokni kichikroq qilib bo'lish
├── 3-urinish: admin/user ga flag qilish
└── HECH QACHON: noto'g'ri quiz ni DB ga yozma

SIFAT BALLARI:
├── 95%+ savol topildi → ✅ AUTO APPROVE
├── 80-95% topildi → ⚠️ USER TASDIQLAYDI
└── <80% topildi → ❌ ADMIN REVIEW
```

### Tezlik Optimizatsiya

```
Parallel processing:
├── 100 savol = 7-10 batch (15 savoldan)
├── Barcha batchlar PARALLEL yuboriladi
├── Jami vaqt: 5-10 soniya (100 savol uchun)
└── 1000 savol ≈ 30-60 soniya

Redis Queue orqali:
├── User fayl yuklaydi → task yaratiladi
├── Celery worker ishga tushadi
├── User "⏳ 30 soniya..." xabarini ko'radi
├── Tayyor bo'lganda → "✅ 98 savol tayyor!" xabari
└── User bot ichida quizni boshlaydi

Caching:
├── Bir xil fayl qayta yuklanmasin (file hash check)
└── AI natijasi cache qilinadi (qayta ishlatish uchun)
```

### AI Engine Papka Strukturasi

```
services/ai-engine/
├── main.py                 ← FastAPI + Celery app
├── parsers/
│   ├── __init__.py
│   ├── detector.py         ← Format detector (Stage 1)
│   ├── word_parser.py      ← .docx extraction
│   ├── pdf_parser.py       ← .pdf extraction
│   ├── excel_parser.py     ← .xlsx extraction
│   ├── image_parser.py     ← Vision API call
│   └── text_parser.py      ← .txt extraction
├── boundary/
│   ├── __init__.py
│   └── splitter.py         ← Boundary detection (Stage 3)
├── ai/
│   ├── __init__.py
│   ├── structurer.py       ← AI batch processing (Stage 4)
│   ├── prompts.py          ← AI prompt templates
│   └── validator.py        ← Output validation (Stage 5)
├── tasks/
│   ├── __init__.py
│   └── process_file.py     ← Celery task (full pipeline)
├── config.py
├── requirements.txt
└── Dockerfile
```

### Qoidalar

```
✅ MUMKIN:
├── Har bir format uchun alohida parser yozish
├── AI ga batch (10-15) savol yuborish
├── Validation fail bo'lsa retry qilish (max 3)
├── File hash orqali dublikat faylni bloklash
└── User ga progress xabar yuborish

❌ MUMKIN EMAS:
├── Butun faylni bir marta AI ga yuborish (katta, qimmat, noaniq)
├── Validation siz AI natijasini DB ga yozish
├── Image ni mayda bo'laklarga bo'lish (kontekst yo'qoladi)
├── Universal/umumiy parser yozish (har format alohida)
└── AI natijasiga ko'r-ko'rona ishonish
```

---

## 8. Environment va Config

```
Qoida: Hech qanday token, key, URL kod ichida bo'lmasin.

Har bir xizmatda faqat o'z o'zgaruvchilari:
.env → docker-compose → xizmat

.env.example fayli har doim to'liq bo'lishi shart.
Haqiqiy .env → .gitignore da bo'lishi shart.
```

---

## 8. Versiyalash va Deploy

```
Har bir xizmat mustaqil deploy qilinadi.
Bir xizmat o'zgarganda boshqasi restart bo'lmaydi.

CI/CD qoidasi:
- main branch → production
- dev branch  → staging
- feature/*   → test

Har bir PR da:
✅ Tests o'tishi shart
✅ Dockerfile build bo'lishi shart
✅ .env.example yangilangan bo'lishi shart
```

---

## 9. Qisqacha Eslatma

```
Yangi xizmat qo'shishdan oldin o'yla:
  → Bu mavjud xizmatga qo'shilishi mumkinmi?
  → Agar yo'q, qaysi til? (Go: tezlik, Python: AI/bot)
  → Muloqot qanday? (HTTP yoki Queue)
  → Qaysi jadvallarga yozadi?

Shubha bo'lsa — ARCHITECTURE.md ni o'qi.
```
