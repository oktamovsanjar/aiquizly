# Quiz Bot — UX Oqimi (User Experience)

## 1. Birinchi Kirish (Onboarding)

```
User /start bosadi
       ↓
┌─────────────────────────────────────────┐
│ Quiz Bot ga xush kelibsiz!              │
│                                         │
│ Bu bot orqali:                          │
│ • Tayyor quizlarni yechishingiz         │
│ • O'z testlaringizni yaratishingiz      │
│ • Do'stlar bilan bellashishingiz mumkin │
│                                         │
│ Tilni tanlang:                          │
│                                         │
│ [O'zbek] [Русский] [English]            │
└─────────────────────────────────────────┘
       ↓
Til tanlagach → Asosiy menyu
```

---

## 2. Asosiy Menyu (Main Menu)

```
┌─────────────────────────────────────────┐
│  [▶️ Boshlash]       [🔍 Qidirish]     │
│  [📤 Quiz Yaratish]  [🏆 Reyting]      │
│  [👤 Profil]         [👥 Taklif qilish] │
└─────────────────────────────────────────┘

Har bir tugma nima qiladi:
├── Boshlash    → O'z quizlarim + ommaviy quizlar
├── Qidirish    → Tag, nom, muallif bo'yicha qidiruv
├── Yaratish    → Fayl yuklash / qo'lda yozish
├── Reyting     → Leaderboard
├── Profil      → Statistika, obuna, yutuqlar
└── Taklif      → Referal link
```

---

## 3. Boshlash Oqimi

```
[▶️ Boshlash] bosadi
       ↓
┌─────────────────────────────────────────┐
│ Qayerdan o'ynaysiz?                     │
│                                         │
│ [📂 Mening quizlarim]                   │
│ [📌 Obunalarim]                          │
│ [🌐 Ommaviy quizlar]                    │
│ [🔥 Trend (eng ko'p o'ynalgan)]         │
│ [🎲 Tasodifiy]                           │
└─────────────────────────────────────────┘
```

### 3.1 Mening Quizlarim

```
[📂 Mening quizlarim]
       ↓
┌─────────────────────────────────────────┐
│ Sizning to'plamlaringiz:                │
│                                         │
│ 📁 Biologiya 9-sinf (48 savol)         │
│    └── Set 1 (20) | Set 2 (20) | Set 3 (8) │
│ 📁 Ingliz tili Grammar (120 savol)     │
│    └── Set 1-6 (20 tadan)              │
│ 📁 Tarix test (35 savol)               │
│    └── Set 1 (20) | Set 2 (15)         │
│                                         │
│ [📤 Yangi quiz yaratish]               │
└─────────────────────────────────────────┘
       ↓
To'plam tanlaydi → Set tanlaydi → Quiz boshlanadi
```

### 3.2 Ommaviy Quizlar + Qidiruv

```
[🌐 Ommaviy quizlar] yoki [🔍 Qidirish]
       ↓
┌─────────────────────────────────────────┐
│ 🔍 Qidiring yoki teg tanlang:          │
│                                         │
│ Trenddagi teglar:                       │
│ [#ingliz_tili] [#matematika] [#dtm]    │
│ [#dasturlash] [#psixologiya] [#ielts]  │
│ [#avtodrom] [#tarix] [#biologiya]      │
│                                         │
│ Yoki matn yozing...                     │
└─────────────────────────────────────────┘
       ↓
User "#dtm" tanlaydi yoki "traffic qoidalari" yozadi
       ↓
┌─────────────────────────────────────────┐
│ Natijalar: "dtm"                        │
│                                         │
│ 📋 DTM Matematika 2025 — @aziz         │
│    ⭐ 4.8 | 👥 1.2k o'ynagan | 200 savol│
│                                         │
│ 📋 DTM Fizika tayyorgarlik — @study_uz │
│    ⭐ 4.5 | 👥 830 o'ynagan | 150 savol │
│                                         │
│ 📋 DTM Ona tili — @teacher_bot         │
│    ⭐ 4.7 | 👥 2.1k o'ynagan | 300 savol│
│                                         │
│ [Keyingi sahifa →]                      │
└─────────────────────────────────────────┘
       ↓
Quiz tanlaydi → set tanlaydi → boshlaydi
```

---

## 4. Quiz Jarayoni (In-Game)

```
Set tanladi (masalan 20 savollik)
       ↓
┌─────────────────────────────────────────┐
│ 📋 "DTM Matematika 2025" — Set 1       │
│ 📏 20 savol                             │
│ ⏱ Har savol: 30 soniya                  │
│                                         │
│ [▶️ Boshlash]  [⏱ Vaqtni o'zgartirish]  │
└─────────────────────────────────────────┘
       ↓
[⏱ Vaqtni o'zgartirish]:
│ [15s] [30s] [45s] [60s]                │
       ↓
[▶️ Boshlash] → Telegram Quiz Poll ketma-ket keladi
       ↓
Har bir savol = 1 Telegram Quiz Poll
├── Savol matni
├── Variantlar (2-10)
├── Timer (user tanlagan)
├── To'g'ri javob → konfetti
├── Noto'g'ri → explanation ko'rsatiladi
└── Keyingi savol avtomatik (2 sek pauza)

STOP (muddatidan oldin to'xtatish):
─────────────────────────────────────
Quiz davomida user /stop yoki [⏹ To'xtatish] bosadi
       ↓
┌─────────────────────────────────────────┐
│ ⏹ Quizni to'xtatmoqchimisiz?           │
│ Hozircha 8/20 savol yechdingiz.         │
│                                         │
│ [⏹ To'xtatish va natija ko'rish]       │
│ [💾 Saqlash (keyinroq davom)]            │
│ [▶️ Davom etish]                         │
└─────────────────────────────────────────┘

"To'xtatish" → faqat yechilgan 8 savoldan natija chiqadi
"Saqlash" → 9-savoldan keyinroq davom eta oladi

AUTO-PAUSE (2 marta javob bermasa):
─────────────────────────────────────
Savol yuborildi → vaqt tugadi → javob yo'q = 1-skip
Keyingi savol → yana javob yo'q = 2-skip
       ↓
┌─────────────────────────────────────────┐
│ ⏸ Quiz pauzaga olindi                   │
│                                         │
│ 2 ta savolga javob bermadingiz.         │
│ Hozir band bo'lsangiz, keyinroq        │
│ davom etishingiz mumkin.                │
│                                         │
│ [▶️ Davom etish]                         │
│ [💾 Saqlash va chiqish]                  │
└─────────────────────────────────────────┘

"Davom etish" → to'xtagan joydan davom (skip qilinganlar hisoblanmaydi)
"Saqlash" → progress saqlanadi, keyinroq qaytib davom eta oladi

Saqlangan quiz:
┌─────────────────────────────────────────┐
│ 📁 Biologiya 9-sinf — Set 3            │
│ ⏸ To'xtagan: 8/20 savol (40%)          │
│ Oxirgi: 2 soat oldin                    │
│                                         │
│ [▶️ Davom (9-savoldan)]  [🔄 Boshidan]  │
└─────────────────────────────────────────┘
```

---

## 5. Quiz Tugashi (Results)

```
┌─────────────────────────────────────────┐
│ Quiz tugadi!                            │
│                                         │
│ Natijangiz:                             │
│ ✅ To'g'ri: 16/20                       │
│ ❌ Noto'g'ri: 3/20                      │
│ ⏭ Javobsiz: 1/20                       │
│                                         │
│ ⏱ Vaqt: 4:12                            │
│ 🏆 Ball: 820 / 1000                    │
│                                         │
│ +15 XP yutdingiz!                       │
│ 🔥 Streak: 6 kun                        │
│                                         │
│ [🔄 Set 2 ga o'tish]                    │
│ [🔁 Xatolarni qayta ishlash]            │
│ [📊 Xatolarni ko'rish]                  │
│ [📤 Natija ulashish]                    │
│ [🏠 Menyu]                              │
└─────────────────────────────────────────┘
```

---

## 5.1 Xatolarni Qayta Ishlash

```
[🔁 Xatolarni qayta ishlash] bosadi
       ↓
┌─────────────────────────────────────────┐
│ 🔁 Xato javob berilgan savollar: 3 ta  │
│                                         │
│ Faqat noto'g'ri javob bergan            │
│ savollaringiz qayta beriladi.           │
│                                         │
│ [▶️ Boshlash (3 savol)]                  │
└─────────────────────────────────────────┘
       ↓
3 ta xato savol qayta quiz poll sifatida keladi
       ↓
Tugagach:
┌─────────────────────────────────────────┐
│ 🔁 Qayta ishlash natijasi:              │
│                                         │
│ ✅ Tuzatildi: 2/3                       │
│ ❌ Yana xato: 1/3                       │
│                                         │
│ Umumiy natija yangilandi:               │
│ 18/20 (90%) — avval 16/20 (80%) edi    │
│                                         │
│ [🔁 Yana 1 ta qoldi]  [🏠 Menyu]       │
└─────────────────────────────────────────┘

QOIDA:
├── Qayta ishlash cheksiz marta mumkin
├── Har safar faqat XATO savollar keladi
├── Barcha to'g'ri → "💯 Hammasi to'g'ri!"
├── Umumiy natija YANGILANADI (eng yaxshisi saqlanadi)
└── XP faqat birinchi o'yinda beriladi (qayta ishlashda yo'q)
```

---

## 6. Quiz Yaratish (AI Import)

```
[📤 Quiz Yaratish] bosadi
       ↓
┌─────────────────────────────────────────┐
│ Quiz yaratish:                          │
│                                         │
│ [📄 Fayl yuklash]   ← Word/PDF/Excel   │
│ [📷 Rasm yuborish]  ← Screenshot/skan  │
│ [✍️ Qo'lda yozish]                      │
└─────────────────────────────────────────┘
```

### 6.1 Fayl Yuklash

```
[📄 Fayl yuklash]
       ↓
┌─────────────────────────────────────────┐
│ Faylni yuboring.                        │
│ (.docx, .pdf, .xlsx, .txt — max 10 MB) │
└─────────────────────────────────────────┘
       ↓
User fayl yuboradi
       ↓
┌─────────────────────────────────────────┐
│ ⏳ Qayta ishlanmoqda...                  │
│ 📄 biologiya_9sinf.docx (245 KB)       │
│ [████████░░ 80%]                        │
└─────────────────────────────────────────┘
       ↓
TAYYOR:
┌─────────────────────────────────────────┐
│ ✅ 500 ta savol topildi!                 │
│                                         │
│ Avtomatik bo'lindi:                     │
│ ├── Set 1: savol 1-20                   │
│ ├── Set 2: savol 21-40                  │
│ ├── ...                                 │
│ └── Set 25: savol 481-500               │
│                                         │
│ To'plam nomi: [Biologiya 9-sinf     ]   │
│ Teglar:       [#biologiya #9sinf    ]   │
│ Quiz guruh:   [📌 DTM Tayyorgarlik ▼]  │
│ Kimga:        (●) Faqat men             │
│               ( ) Ommaviy               │
│                                         │
│ [✅ Saqlash]  [👁 Ko'rib chiqish]       │
└─────────────────────────────────────────┘

Quiz guruhga biriktirsa → barcha obunachilarga xabar ketadi.

500 savol → avtomatik 25 ta set (20 tadan)
User hech narsa qilmaydi, bot o'zi bo'ladi.
```

### 6.2 Xatolik bo'lsa

```
┌─────────────────────────────────────────┐
│ ⚠️ 497/500 savol tayyor                  │
│                                         │
│ 3 ta savolda muammo:                    │
│ • #42: variant topilmadi               │
│ • #198: to'g'ri javob aniqlanmadi       │
│ • #301: matn buzilgan                   │
│                                         │
│ [⏭ O'tkazib yuborish (497 ta saqlash)] │
│ [✏️ Qo'lda tuzatish]                    │
└─────────────────────────────────────────┘

Ko'p holda user "o'tkazib yuborish" ni tanlaydi.
3 ta savol yo'qolsa — muammo emas.
```

### 6.3 Rasm Yuborish

```
[📷 Rasm yuborish]
       ↓
┌─────────────────────────────────────────┐
│ Test rasmlarini yuboring.               │
│ Bir nechta rasm yuborishingiz mumkin.   │
│ Tayyor bo'lgach "Tamom" bosing.         │
└─────────────────────────────────────────┘
       ↓
User rasmlar yuboradi
       ↓
[📷 Yana]  [✅ Tamom]
       ↓
[✅ Tamom] → AI Vision pipeline → natija (yuqoridagi kabi)
```

---

## 7. To'plam va Ulashish (Collections)

```
To'plam = bir fayldan kelgan barcha savollar
Set = 20 savollik o'yin bloki

To'plam ulashish (Premium):
       ↓
┌─────────────────────────────────────────┐
│ 📁 "Biologiya 9-sinf"                   │
│ 500 savol | 25 set                      │
│                                         │
│ [▶️ O'ynash]                             │
│ [📤 Ulashish]                           │
│ [✏️ Tahrirlash]                          │
│ [🗑 O'chirish]                           │
└─────────────────────────────────────────┘
       ↓
[📤 Ulashish] bosadi
       ↓
┌─────────────────────────────────────────┐
│ Ulashish usuli:                         │
│                                         │
│ [🔗 Link yaratish]                      │
│    → t.me/quizbot?start=abc123         │
│    → Kim olsa shu quizni o'ynay oladi  │
│                                         │
│ [👥 Guruhga yuborish]                   │
│    → Guruh tanlash                     │
│                                         │
│ [🌐 Ommaviy qilish]                     │
│    → Barchaga ko'rinadi, qidiruvda chiqadi │
└─────────────────────────────────────────┘
```

### Boshqa user link orqali kirsa:

```
t.me/quizbot?start=abc123
       ↓
┌─────────────────────────────────────────┐
│ 📋 "Biologiya 9-sinf" — @sanjar        │
│ 500 savol | 25 set                      │
│                                         │
│ [▶️ Set 1 dan boshlash]                  │
│ [📥 O'zimga saqlash]                    │
└─────────────────────────────────────────┘
```

---

## 8. Qidiruv Tizimi

```
[🔍 Qidirish] yoki istalgan matn yozsa
       ↓
Qidiruv nima bo'yicha ishlaydi:
├── Teglar: #dtm, #ingliz_tili, #matematika
├── Quiz nomi: "traffic qoidalari"
├── Muallif: @username
└── Mazmun: savol ichidagi so'zlar

Natija tartibi:
├── 1. O'ynalgan soni (mashhurligi)
├── 2. Reyting (yulduzchalar)
└── 3. Yangilik (sanasi)
```

---

## 9. Rag'batlantirish Tizimi (Gamification)

### XP (Experience Points)

```
Har bir harakat uchun XP:
├── Quiz yechish:        +10 XP
├── 100% to'g'ri:        +25 XP (bonus)
├── Kunlik streak:       +5 XP * kun soni
├── Quiz yaratish:       +20 XP
├── Referal:             +50 XP
└── Haftalik top 10:     +100 XP
```

### Darajalar (Levels)

```
XP → Daraja:
├── 0-100 XP:      🌱 Yangi
├── 100-500 XP:    📗 O'rganuvchi
├── 500-2000 XP:   📘 Bilimdon
├── 2000-5000 XP:  📙 Ustoz
├── 5000-15000 XP: 📕 Professor
└── 15000+ XP:     👑 Akademik

Daraja profilda ko'rinadi.
Leaderboard da daraja iconi chiqadi.
```

### Yutuqlar (Achievements)

```
Bir martalik mukofotlar:
├── 🎯 "Birinchi quiz" — birinchi quiz yechish
├── 🔥 "7 kunlik streak" — ketma-ket 7 kun
├── 💯 "Mukammal" — biror setda 100% to'g'ri
├── 📤 "Muallif" — birinchi quiz yaratish
├── 👥 "Ulashuvchi" — quiz ulashish
├── 🏆 "Top 10" — haftalik reytingga kirish
├── 📚 "1000 savol" — jami 1000 savolga javob berish
└── 👑 "Akademik" — eng yuqori darajaga yetish
```

### Streak (Ketma-ketlik)

```
Har kuni kamida 1 quiz yechsa → streak davom etadi
┌─────────────────────────────────────────┐
│ 🔥 Streak: 12 kun                       │
│ ├── Bugun: ✅                            │
│ ├── Kecha: ✅                            │
│ └── ...                                 │
│                                         │
│ Keyingi mukofot: 14 kun (🎁 +100 XP)    │
└─────────────────────────────────────────┘

Streak buzilsa:
┌─────────────────────────────────────────┐
│ 😔 Streak uzildi (12 kun edi)            │
│ Qaytadan boshlang!                      │
│                                         │
│ [▶️ Tez quiz (5 savol)]                 │
└─────────────────────────────────────────┘
```

---

## 10. Referal Tizimi

```
[👥 Taklif qilish] bosadi
       ↓
┌─────────────────────────────────────────┐
│ 👥 Do'stlaringizni taklif qiling!       │
│                                         │
│ Sizning link:                           │
│ t.me/quizbot?start=ref_sanjar123       │
│                                         │
│ Har bir taklif uchun:                   │
│ ├── Siz: +50 XP + 3 kun premium        │
│ └── Do'st: +20 XP bonus                │
│                                         │
│ 📊 Statistika:                          │
│ ├── Taklif qilingan: 8 kishi          │
│ ├── Ro'yxatdan o'tgan: 5 kishi        │
│ └── Yutgan bonus: 15 kun premium       │
│                                         │
│ [📤 Ulashish]  [📋 Link nusxalash]     │
└─────────────────────────────────────────┘

Referal mukofotlari:
├── 5 ta referal:  🥉 Bronza badge + 7 kun premium
├── 20 ta referal: 🥈 Kumush badge + 30 kun premium
├── 50 ta referal: 🥇 Oltin badge + 90 kun premium
└── 100 ta referal: 💎 Elchi statusi + 1 yil premium
```

---

## 11. Profil

```
[👤 Profil] bosadi
       ↓
┌─────────────────────────────────────────┐
│ 👤 Sanjar                               │
│ 📘 Bilimdon (1,250 XP)                  │
│ 🔥 Streak: 12 kun                       │
│                                         │
│ 📊 Statistika:                          │
│ ├── O'ynagan: 142 quiz                 │
│ ├── To'g'ri: 73%                       │
│ ├── Eng yaxshi: 98% (Tarix)            │
│ └── Jami savollar: 2,840               │
│                                         │
│ 🏅 Yutuqlar: 5/12                       │
│ 🎯💯📤👥🔥                              │
│                                         │
│ 💎 Tarif: Premium (→ 2026-07-15)        │
│ 📚 Quizlarim: 12 to'plam              │
│                                         │
│ [📊 Batafsil]  [💎 Obuna]  [⚙️ Sozlama]│
└─────────────────────────────────────────┘
```

---

## 12. Reyting (Leaderboard)

```
[🏆 Reyting] bosadi
       ↓
┌─────────────────────────────────────────┐
│ 🏆 Reyting                              │
│                                         │
│ [Bugun] [Hafta] [Oy] [Barchasi]        │
│                                         │
│ 🥇 Aziz (📕 Ustoz) — 4,520 ball        │
│ 🥈 Dilshod (📙 Ustoz) — 4,180 ball     │
│ 🥉 Madina (📘 Bilimdon) — 3,950 ball   │
│ 4. Jasur — 3,720                        │
│ 5. Nilufar — 3,510                     │
│ ...                                     │
│ ─────────────────────                   │
│ 📍 Siz: #156 — 820 ball                │
│                                         │
│ [Teg bo'yicha: #dtm ▼]                 │
└─────────────────────────────────────────┘
```

---

## 13. Quiz Guruh (Kanal Konsepti)

```
Quiz Guruh = foydalanuvchining quiz kanali.
Telegram guruh EMAS. Bot ichidagi virtual guruh.

Maqsad:
├── Auditoriya yig'ish (obunachi = subscriber)
├── Yangi quiz qo'shilsa → obunachilarga xabar
├── Bir user bir nechta quiz guruh yarata oladi
└── Boshqalar obuna bo'lib, quizlarni o'ynaydi
```

### 13.1 Quiz Guruh Yaratish

```
Profil → [📌 Quiz Guruhlarim] → [+ Yangi guruh]
       ↓
┌─────────────────────────────────────────┐
│ Yangi quiz guruh yaratish:              │
│                                         │
│ Nom: [DTM Tayyorgarlik 2025      ]     │
│ Tavsif: [Har kuni DTM testlari   ]     │
│ Teglar: [#dtm #abiturient        ]     │
│                                         │
│ [✅ Yaratish]                            │
└─────────────────────────────────────────┘
       ↓
┌─────────────────────────────────────────┐
│ ✅ Quiz guruh yaratildi!                 │
│                                         │
│ 📌 "DTM Tayyorgarlik 2025"             │
│ Link: t.me/quizbot?start=g_dtm2025     │
│                                         │
│ Endi quiz yaratib, shu guruhga          │
│ biriktiring — obunachilarga xabar       │
│ ketadi.                                 │
│                                         │
│ [📤 Link ulashish]  [📂 Quiz biriktirish] │
└─────────────────────────────────────────┘
```

### 13.2 Quiz Guruhni Boshqarish

```
📌 Quiz Guruhlarim
       ↓
┌─────────────────────────────────────────┐
│ Sizning quiz guruhlaringiz:             │
│                                         │
│ 📌 DTM Tayyorgarlik 2025               │
│    👥 1,240 obunachi | 📚 15 to'plam   │
│                                         │
│ 📌 Ingliz tili IELTS                    │
│    👥 830 obunachi | 📚 8 to'plam      │
│                                         │
│ [+ Yangi guruh]                         │
└─────────────────────────────────────────┘
       ↓
Guruhni tanlasa:
┌─────────────────────────────────────────┐
│ 📌 DTM Tayyorgarlik 2025               │
│ 👥 1,240 obunachi                       │
│                                         │
│ To'plamlar:                             │
│ ├── Matematika 2025 (200 savol)        │
│ ├── Fizika 2025 (150 savol)            │
│ └── Ona tili (300 savol)               │
│                                         │
│ [📂 Quiz biriktirish]                   │
│ [📢 Xabar yuborish]                     │
│ [📊 Statistika]                         │
│ [⚙️ Sozlamalar]                         │
│ [📤 Link ulashish]                      │
└─────────────────────────────────────────┘
```

### 13.3 Obuna Bo'lish (subscriber)

```
Boshqa user quiz guruh linkini ochsa:
t.me/quizbot?start=g_dtm2025
       ↓
┌─────────────────────────────────────────┐
│ 📌 "DTM Tayyorgarlik 2025" — @sanjar   │
│ 👥 1,240 obunachi                       │
│ 📚 15 to'plam | 650 savol              │
│                                         │
│ Eng yangi: "Matematika 2025" (2 kun)   │
│ Eng mashhur: "Fizika 2025" (⭐ 4.8)    │
│                                         │
│ [📌 Obuna bo'lish]  [▶️ O'ynash]        │
└─────────────────────────────────────────┘
       ↓
Obuna bo'lgach → asosiy menyuda [📌 Obunalarim] da ko'rinadi
Yangi quiz qo'shilganda → notification keladi
```

### 13.4 Obunalarim

```
[📌 Obunalarim]
       ↓
┌─────────────────────────────────────────┐
│ Obunalaringiz:                          │
│                                         │
│ 📌 DTM Tayyorgarlik — @sanjar          │
│    🆕 Yangi: "Kimyo 2025" (bugun)      │
│                                         │
│ 📌 English Grammar — @teacher_pro      │
│    Oxirgi: 3 kun oldin                  │
│                                         │
│ 📌 Avtodrom testlar — @driving_uz      │
│    Oxirgi: 1 hafta oldin               │
└─────────────────────────────────────────┘
       ↓
Tanlasa → shu guruhdagi to'plamlar → o'ynash
```

### 13.5 Yangi Quiz Qo'shilganda (notification)

```
Owner yangi quiz qo'shdi → barcha obunachilarga:
┌─────────────────────────────────────────┐
│ 📌 DTM Tayyorgarlik — yangi quiz!       │
│                                         │
│ 📋 "Kimyo organik birikmalar"           │
│ 40 savol | 2 set                        │
│                                         │
│ [▶️ O'ynash]  [📌 Guruhga o'tish]       │
└─────────────────────────────────────────┘
```

---

## 14. Telegram Guruhda Ishlash

```
MUHIM: Telegram guruh ≠ Quiz guruh
├── Quiz guruh = bot ichidagi kanal (auditoriya)
└── Telegram guruh = Telegram chat (birgalikda o'ynash)
```

### 14.1 Botni Telegram Guruhga Qo'shish

```
Bot guruhga qo'shilganda:
       ↓
┌─────────────────────────────────────────┐
│ Quiz Bot guruhga qo'shildi!             │
│                                         │
│ Admin buyruqlari:                       │
│ /quiz — quiz boshlash                  │
│ /settings — guruh sozlamalari          │
│ /top — guruh reytingi                  │
└─────────────────────────────────────────┘
```

### 14.2 Guruh Sozlamalari

```
Admin: /settings
       ↓
┌─────────────────────────────────────────┐
│ ⚙️ Guruh sozlamalari:                   │
│                                         │
│ Voting: [✅ Yoqilgan / ❌ O'chirilgan]   │
│ → Yoqilgan: a'zolar voting bilan       │
│   quiz boshlashni tasdiqlay oladi       │
│                                         │
│ Kim quiz boshlatishi mumkin:            │
│ (●) Faqat admin                        │
│ ( ) Barcha a'zolar                      │
│                                         │
│ [💾 Saqlash]                            │
└─────────────────────────────────────────┘
```

### 14.3 Voting bilan Quiz Boshlash

```
Voting YOQILGAN holatda:

Admin yoki a'zo: /quiz
       ↓
Quiz tanlaydi
       ↓
┌─────────────────────────────────────────┐
│ 🗳 Quiz boshlashga ovoz bering!         │
│                                         │
│ 📋 "DTM Matematika" — Set 3 (20 savol) │
│ ⏱ Har savol: 30 soniya                  │
│                                         │
│ Boshlash uchun kamida 3 kishi kerak.    │
│                                         │
│ ✅ Tayyorman: 5 kishi                    │
│ [✅ Men ham tayyorman!]                  │
│                                         │
│ ⏳ Kutish: 60 soniya                     │
└─────────────────────────────────────────┘
       ↓
60 soniya tugagach YOKI admin "Boshlash" desa:
       ↓
Kamida 3 kishi bo'lsa → Quiz boshlanadi
3 dan kam → "Yetarli ishtirokchi yo'q"

Voting O'CHIRILGAN holatda:
Admin: /quiz → tanlaydi → darhol boshlanadi
```

### 14.4 Telegram Guruhda Quiz Jarayoni

```
Quiz boshlanadi → har bir savol = Quiz Poll
       ↓
Barcha a'zolar real-time javob beradi
       ↓
Tugagach:
┌─────────────────────────────────────────┐
│ 🏁 Quiz natijasi:                       │
│                                         │
│ 🥇 Aziz — 18/20 (1:42)                 │
│ 🥈 Madina — 17/20 (2:05)               │
│ 🥉 Jasur — 15/20 (1:38)                │
│ 4. Sanjar — 14/20                       │
│ ...                                     │
│                                         │
│ Qatnashganlar: 12 kishi                 │
│ O'rtacha: 72%                           │
│                                         │
│ [🔄 Yana o'ynash]  [📊 Batafsil]       │
└─────────────────────────────────────────┘
```

---

## 15. Notification Oqimi

```
Kunlik eslatma (streak uchun):
┌─────────────────────────────────────────┐
│ 🔥 12 kunlik streak!                     │
│ Bugun ham davom ettiring.               │
│ [▶️ Tez quiz (5 savol)]                 │
└─────────────────────────────────────────┘

Quiz tayyor:
┌─────────────────────────────────────────┐
│ ✅ "Biologiya 9-sinf" tayyor!            │
│ 500 savol → 25 set                      │
│ [▶️ Boshlash]                           │
└─────────────────────────────────────────┘

Quiz guruh yangilanishi (obunachilarga):
┌─────────────────────────────────────────┐
│ 📌 DTM Tayyorgarlik — yangi quiz!       │
│ 📋 "Kimyo organik birikmalar"           │
│ 40 savol | 2 set                        │
│ [▶️ O'ynash]                            │
└─────────────────────────────────────────┘

Yangi yutuq:
┌─────────────────────────────────────────┐
│ 🏅 Yangi yutuq: "7 kunlik streak"!      │
│ +50 XP qo'shildi                        │
│ [👤 Profilga]                           │
└─────────────────────────────────────────┘

Referal kirganda:
┌─────────────────────────────────────────┐
│ 👥 Do'stingiz @aziz ro'yxatdan o'tdi!   │
│ +50 XP va +3 kun premium qo'shildi     │
└─────────────────────────────────────────┘
```

---

## 16. Premium Paywall

```
Limit ga yetganda:
┌─────────────────────────────────────────┐
│ Bu oyda 3/3 fayl yuklagansiz.           │
│                                         │
│ Premium bilan:                          │
│ • Cheksiz yuklash                       │
│ • Guruhga ulashish                      │
│ • Quiz doim saqlanadi                   │
│                                         │
│ 💰 29,000 so'm/oy                       │
│    249,000 so'm/yil (29% tejash)        │
│                                         │
│ Yoki 3 ta do'st taklif qiling =         │
│ 9 kun bepul premium!                    │
│                                         │
│ [⭐ Telegram Stars] [💳 Payme]          │
│ [👥 Taklif qilib yutish]               │
└─────────────────────────────────────────┘
```

---

## 17. Vaqt Tanlash

```
Quiz boshlanishidan oldin:
┌─────────────────────────────────────────┐
│ ⏱ Har bir savol uchun vaqt:             │
│                                         │
│ [15s]  [30s]  [45s]  [60s]             │
│                                         │
│ 💡 Tavsiya: 30 soniya                   │
└─────────────────────────────────────────┘

User tanlaydi. Default: 30s.
```

---

## 18. To'plam Avtomatik Bo'linishi

```
QOIDA: 1 ta set = 20 savol (default).
       User o'zgartira oladi: 10 / 20 / 30 / 50

Misol: 500 savollik fayl yuklandi
       ↓
Avtomatik:
├── Set 1:  savol 1-20
├── Set 2:  savol 21-40
├── ...
└── Set 25: savol 481-500

User setni bittadan yechadi.
Har bir set tugagach → natija ko'rsatiladi.
Keyingi setga o'tishi mumkin.

Progress:
┌─────────────────────────────────────────┐
│ 📁 Biologiya 9-sinf                     │
│ ████████░░░░░░░░░░░░░░░░░ 8/25 set     │
│                                         │
│ ✅ Set 1: 18/20 (90%)                   │
│ ✅ Set 2: 15/20 (75%)                   │
│ ...                                     │
│ ✅ Set 8: 17/20 (85%)                   │
│ ▶️ Set 9: hali o'ynalmagan              │
│ ...                                     │
└─────────────────────────────────────────┘
```

---

## 19. State Machine

```
IDLE
├── Asosiy menyu
├── Istalgan tugma bosilishi mumkin
└── /cancel → IDLE

QUIZ_SETUP
├── To'plam → Set → Vaqt tanlash
└── /cancel → IDLE

QUIZ_PLAYING
├── Poll lar kelmoqda
├── /stop → STOPPED
├── 2x skip → PAUSED
└── Oxirgi savol → RESULT → IDLE

PAUSED (2 marta javob bermasa)
├── "Davom etish" → QUIZ_PLAYING
├── "Saqlash" → progress DB da, IDLE
└── Keyinroq qaytib davom eta oladi

STOPPED (user o'zi to'xtatsa)
├── "Natija ko'rish" → RESULT (faqat yechilganlar)
├── "Saqlash" → progress DB da, IDLE
└── RESULT → IDLE

FILE_UPLOAD
├── Fayl/rasm kutilmoqda
└── /cancel → IDLE

PROCESSING
├── AI ishlayapti, user kutadi
└── Tugadi → REVIEW

REVIEW
├── Natijani tasdiqlash
└── Tasdiqladi/Bekor → IDLE

MANUAL_CREATE
├── Savol → Variant → Javob → Yana?
└── /cancel → IDLE
```

---

## 20. UX Qoidalari

```
✅ QILISH:
├── Har bir ekranda "orqaga" yoki "bekor"
├── Xatolikda: nima bo'ldi + nima qilish kerak
├── Progress bar (AI ishlayotganda)
├── 3 soniyadan ko'p javob kelmasa → "⏳" xabari
├── Tugmalar max 6 ta (2x3 grid)
├── Matn qisqa: max 3-4 qator
└── Har bir harakatdan keyin feedback

❌ QILMASLIK:
├── Userni javobsiz qoldirish
├── 10+ tugma ko'rsatish
├── Quiz o'rtasida boshqa narsaga javob berish
├── Technical error message
├── Ortiqcha qadam (3 bosishda natijaga yetish)
└── Bir xil tugma ikki joyda turli ma'noda
```

---

## 21. Bot Buyruqlari

```
/start      — Botni boshlash
/quiz       — Tez quiz (oxirgi to'plamdan)
/create     — Quiz yaratish
/profile    — Profil
/top        — Reyting
/invite     — Referal link
/stop       — Quiz ni to'xtatish
/settings   — Sozlamalar
/help       — Yordam
/cancel     — Bekor qilish
```
