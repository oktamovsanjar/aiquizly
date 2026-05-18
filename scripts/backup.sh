#!/usr/bin/env bash
# ════════════════════════════════════════════════════════════════
#  quiz-bot — TO'LIQ ZAXIRA NUSXASI
#
#  Nima saqlaydi:
#    ✅ PostgreSQL to'liq dump (schema + data)
#    ✅ Butun loyiha kodi (git tarixi bilan)
#    ✅ .env (barcha API kalitlar va parollar)
#    ✅ Infra fayllar (docker-compose, redis.conf, init.sql)
#    ✅ Tiklanish yo'riqnomasi (RESTORE.md)
#
#  Parol: P1l2a3y4%  (zip -P)
#
#  Ishlatish:
#    ./scripts/backup.sh
#
#  Avtomatik (cron):
#    0 21 * * * cd /home/sanjaroktamovorg/quiz-bot && ./scripts/backup.sh
# ════════════════════════════════════════════════════════════════
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

# ── .env dan o'qish ─────────────────────────────────────────────
if [[ -f "$ROOT_DIR/.env" ]]; then
    set -a
    # shellcheck disable=SC1091
    source "$ROOT_DIR/.env"
    set +a
fi

BOT_TOKEN="${TELEGRAM_BOT_TOKEN:-}"
ADMIN_ID="${ADMIN_TELEGRAM_ID:-7537966029}"
ZIP_PASSWORD="P1l2a3y4%"
TIMESTAMP="$(date '+%Y-%m-%d_%H-%M-%S')"
STAGE="quiz_backup_${TIMESTAMP}"
STAGE_DIR="/tmp/${STAGE}"
ZIP_NAME="full_backup_${TIMESTAMP}.zip"
ZIP_PATH="/tmp/${ZIP_NAME}"
MAX_TG_SIZE=$((49 * 1024 * 1024))   # 49 MB — Telegram limiti

# ── Token tekshirish ─────────────────────────────────────────────
if [[ -z "$BOT_TOKEN" ]]; then
    echo "❌ TELEGRAM_BOT_TOKEN topilmadi (.env yoki muhit o'zgaruvchisida)" >&2
    exit 1
fi

echo "════════════════════════════════════"
echo "📦 BACKUP BOSHLANDI: $TIMESTAMP"
echo "════════════════════════════════════"

# ── Papka tuzilmasi ──────────────────────────────────────────────
mkdir -p \
    "$STAGE_DIR/db" \
    "$STAGE_DIR/code" \
    "$STAGE_DIR/secrets" \
    "$STAGE_DIR/infra"

# ══════════════════════════════════════
# 1. POSTGRESQL TO'LIQ DUMP
# ══════════════════════════════════════
echo ""
echo "🗄️  [1/5] PostgreSQL dump olinmoqda..."
DB_DUMP="$STAGE_DIR/db/quiz_bot_${TIMESTAMP}.sql"

if docker compose -f "$ROOT_DIR/docker-compose.yml" exec -T postgres \
    pg_dump -U user --no-password quiz_bot > "$DB_DUMP" 2>/dev/null; then
    DB_SIZE=$(du -sh "$DB_DUMP" 2>/dev/null | cut -f1)
    echo "  ✅ Dump: $DB_SIZE"
else
    echo "  ⚠️  pg_dump xatosi — davom etamiz"
    echo "pg_dump muvaffaqiyatsiz bo'ldi: $(date)" > "$DB_DUMP"
fi

# ── Statistika ───────────────────────────────────────────────────
psql_q() {
    docker compose -f "$ROOT_DIR/docker-compose.yml" exec -T postgres \
        psql -U user -d quiz_bot -tAc "$1" 2>/dev/null | tr -d '[:space:]'
}

USER_COUNT=$(psql_q "SELECT COUNT(*) FROM users;" 2>/dev/null) || USER_COUNT="?"
QUIZ_COUNT=$(psql_q "SELECT COUNT(*) FROM quizzes;" 2>/dev/null) || QUIZ_COUNT="?"
GAME_COUNT=$(psql_q "SELECT COUNT(*) FROM games;" 2>/dev/null) || GAME_COUNT="?"
Q_COUNT=$(psql_q "SELECT COUNT(*) FROM questions;" 2>/dev/null) || Q_COUNT="?"

echo "  📊 Userlar: $USER_COUNT | Quizlar: $QUIZ_COUNT | Savollar: $Q_COUNT | O'yinlar: $GAME_COUNT"

# ══════════════════════════════════════
# 2. LOYIHA KODI (git tarixi bilan)
# ══════════════════════════════════════
echo ""
echo "💻 [2/5] Kod nusxalanmoqda..."

rsync -a --quiet \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='*.pyo' \
    --exclude='.pytest_cache' \
    --exclude='*.egg-info' \
    --exclude='node_modules' \
    --exclude='vendor' \
    --exclude='.mypy_cache' \
    --exclude='*.log' \
    "$ROOT_DIR/" "$STAGE_DIR/code/quiz-bot/" 2>/dev/null || {
    # rsync yo'q bo'lsa cp bilan
    cp -r "$ROOT_DIR/." "$STAGE_DIR/code/quiz-bot/" 2>/dev/null || true
    # Keraksizlarni o'chirish
    find "$STAGE_DIR/code/quiz-bot" -name '__pycache__' -exec rm -rf {} + 2>/dev/null || true
    find "$STAGE_DIR/code/quiz-bot" -name '*.pyc' -delete 2>/dev/null || true
}

CODE_SIZE=$(du -sh "$STAGE_DIR/code" 2>/dev/null | cut -f1)
echo "  ✅ Kod hajmi: $CODE_SIZE"

# ══════════════════════════════════════
# 3. SECRET / ENV FAYLLAR
# ══════════════════════════════════════
echo ""
echo "🔑 [3/5] Secret fayllar saqlanmoqda..."

# Asosiy .env
[[ -f "$ROOT_DIR/.env" ]] && cp "$ROOT_DIR/.env" "$STAGE_DIR/secrets/.env"

# Boshqa .env.* fayllar (agar mavjud bo'lsa)
find "$ROOT_DIR" -maxdepth 2 -name '.env.*' -not -path '*/.git/*' \
    -exec cp {} "$STAGE_DIR/secrets/" \; 2>/dev/null || true

echo "  ✅ Secrets saqlandi"

# ══════════════════════════════════════
# 4. INFRA FAYLLAR
# ══════════════════════════════════════
echo ""
echo "⚙️  [4/5] Infra fayllar saqlanmoqda..."

cp "$ROOT_DIR/docker-compose.yml" "$STAGE_DIR/infra/" 2>/dev/null || true
[[ -f "$ROOT_DIR/docker-compose.test.yml" ]] && \
    cp "$ROOT_DIR/docker-compose.test.yml" "$STAGE_DIR/infra/" 2>/dev/null || true
[[ -d "$ROOT_DIR/infra" ]] && \
    cp -r "$ROOT_DIR/infra/" "$STAGE_DIR/infra/configs/" 2>/dev/null || true
[[ -d "$ROOT_DIR/shared/migrations" ]] && \
    cp -r "$ROOT_DIR/shared/migrations/" "$STAGE_DIR/infra/migrations/" 2>/dev/null || true

echo "  ✅ Infra fayllar saqlandi"

# ══════════════════════════════════════
# 5. TIKLANISH YO'RIQNOMASI
# ══════════════════════════════════════
cat > "$STAGE_DIR/RESTORE.md" << 'RESTORE_EOF'
# Quiz Bot — Tiklash yo'riqnomasi

## Kerak bo'lganlar
- Docker 24+ va Docker Compose 2.x
- Linux server (Ubuntu 20.04+ tavsiya)

## Qadam 1 — Kodni joylashtirish
```bash
cp -r code/quiz-bot /home/sanjaroktamovorg/quiz-bot
cd /home/sanjaroktamovorg/quiz-bot
cp backup/secrets/.env .env
```

## Qadam 2 — Infra ishga tushirish
```bash
docker compose up -d postgres redis
sleep 10   # DB tayyor bo'lguncha kuting
```

## Qadam 3 — DB tiklash
```bash
# Dump faylini topib import qiling:
cat db/quiz_bot_*.sql | docker compose exec -T postgres psql -U user quiz_bot
```

## Qadam 4 — Barcha servislarni ishga tushirish
```bash
docker compose up -d
docker compose ps   # barcha servislar "healthy" bo'lishi kerak
```

## Qadam 5 — Tekshirish
```bash
docker compose logs bot --tail=20
curl http://localhost:8000/health
```

## Eslatma
- .env faylidagi barcha tokenlar va API kalitlar saqlanib qolgan
- Agar bot webhook rejimida ishlagan bo'lsa, WEBHOOK_URL ni yangilang
RESTORE_EOF

echo "  ✅ RESTORE.md yozildi"

# ══════════════════════════════════════
# ZIP (PAROL BILAN)
# ══════════════════════════════════════
echo ""
echo "🗜️  [5/5] ZIP paket yaratilmoqda (parollanadi)..."
cd /tmp
zip -qr -P "$ZIP_PASSWORD" "$ZIP_PATH" "${STAGE}/" 2>/dev/null

ZIP_SIZE_BYTES=$(stat -c%s "$ZIP_PATH" 2>/dev/null || echo "0")
ZIP_SIZE_MB=$(awk "BEGIN {printf \"%.2f\", $ZIP_SIZE_BYTES/1048576}")
echo "  ✅ ZIP hajmi: ${ZIP_SIZE_MB} MB"

# ══════════════════════════════════════
# TELEGRAM GA YUBORISH
# ══════════════════════════════════════
echo ""
echo "📤 Telegram ga yuborilmoqda → ID: $ADMIN_ID"

CAPTION="💾 <b>Zaxira nusxasi (Bot orqali avtomatik)</b>

📅 Sana: ${TIMESTAMP//_/ }
📦 Hajmi: ${ZIP_SIZE_MB} MB
🔐 Parol: <code>P1l2a3y4%</code>

👥 Userlar: ${USER_COUNT}
📋 Quizlar: ${QUIZ_COUNT}
❓ Savollar: ${Q_COUNT}
🎮 O'yinlar: ${GAME_COUNT}

📂 Tarkib:
• 🗄 DB dump (SQL)
• 💻 Butun loyiha kodi (git tarixi bilan)
• 🔑 .env (barcha secretlar)
• ⚙️ Infra + migratsiyalar
• 📖 RESTORE.md (tiklash yo'riqnomasi)"

if [[ "$ZIP_SIZE_BYTES" -gt "$MAX_TG_SIZE" ]]; then
    # Fayl juda katta — faqat xabar yuboramiz
    CAPTION="⚠️ Backup fayli juda katta (${ZIP_SIZE_MB} MB > 49 MB) — Telegram limitidan oshdi.

📅 Sana: ${TIMESTAMP//_/ }
👥 Userlar: ${USER_COUNT} | Quizlar: ${QUIZ_COUNT}

Backup serverda saqlandi: /tmp/${ZIP_NAME}
Qo'lda yuklab olish kerak."
    curl -s -X POST "https://api.telegram.org/bot${BOT_TOKEN}/sendMessage" \
        -F "chat_id=${ADMIN_ID}" \
        -F "text=${CAPTION}" \
        -F "parse_mode=HTML" > /dev/null
    echo "  ⚠️  Fayl ${ZIP_SIZE_MB}MB — juda katta, faqat xabar yuborildi"
    echo "     Fayl saqlab qolindi: $ZIP_PATH"
else
    TG_RESP=$(curl -s -X POST "https://api.telegram.org/bot${BOT_TOKEN}/sendDocument" \
        -F "chat_id=${ADMIN_ID}" \
        -F "document=@${ZIP_PATH};filename=${ZIP_NAME}" \
        -F "caption=${CAPTION}" \
        -F "parse_mode=HTML")

    if echo "$TG_RESP" | grep -q '"ok":true'; then
        echo "  ✅ Telegram ga muvaffaqiyatli yuborildi!"
        rm -rf "$STAGE_DIR" "$ZIP_PATH"
    else
        TG_ERR=$(echo "$TG_RESP" | grep -o '"description":"[^"]*"' | head -1)
        echo "  ❌ Telegram xatosi: $TG_ERR"
        echo "     Fayl saqlab qolindi: $ZIP_PATH"
        rm -rf "$STAGE_DIR"
    fi
fi

echo ""
echo "════════════════════════════════════"
echo "✅ BACKUP TUGADI: $TIMESTAMP"
echo "════════════════════════════════════"
