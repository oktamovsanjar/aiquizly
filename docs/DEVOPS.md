# Quiz Bot — DevOps

## 1. Infrastructure Diagramma

```
                    Internet
                       │
                       ▼
              ┌────────────────┐
              │   Cloudflare   │  ← DDoS himoya, SSL
              │   (DNS + CDN)  │
              └───────┬────────┘
                      │
                      ▼
              ┌────────────────┐
              │     Nginx      │  ← Reverse proxy, rate limiting
              │   (Load Bal.)  │
              └───────┬────────┘
                      │
         ┌────────────┼─────────────┐
         ▼            ▼             ▼
   ┌──────────┐ ┌──────────┐ ┌──────────┐
   │ Gateway  │ │ Gateway  │ │ Gateway  │   ← Go (x3)
   │ :8080    │ │ :8081    │ │ :8082    │
   └────┬─────┘ └────┬─────┘ └────┬─────┘
        │             │             │
        └──────┬──────┘─────────────┘
               ▼
   ┌───────────────────────────────────────┐
   │           Internal Network            │
   ├───────────┬────────────┬──────────────┤
   │           │            │              │
   ▼           ▼            ▼              ▼
┌───────┐ ┌────────┐ ┌──────────┐ ┌───────────┐
│Bot x4 │ ��Game x2 │ │AI Eng x4 │ │Notifier x2│
│Python │ │Go      │ │Python    │ │Go         │
└───┬───┘ └───┬────┘ └────┬─────┘ └─────┬─────┘
    │         │            │             ���
    └─────────┼────────────┼─────────────┘
              ▼            ▼
   ┌──────────────┐ ┌──────────────┐
   │ PostgreSQL   │ │    Redis     │
   │ (Primary +   │ │  (Cluster)   │
   │  Replica)    │ │              │
   └──────────────┘ └──────────────┘
```

---

## 2. Docker Sozlamalari

### docker-compose.yml (Development)

```yaml
version: "3.8"

services:
  # === GO SERVICES ===
  gateway:
    build: ./services/gateway
    ports:
      - "8080:8080"
    environment:
      - REDIS_URL=redis://redis:6379/0
      - BOT_SERVICE_URL=http://bot:8000
      - GAME_SERVICE_URL=http://game:8081
    depends_on:
      - redis
    restart: unless-stopped

  game:
    build: ./services/game
    ports:
      - "8081:8081"
    environment:
      - DATABASE_URL=postgres://user:pass@postgres:5432/quiz_bot
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - postgres
      - redis
    restart: unless-stopped

  notifier:
    build: ./services/notifier
    environment:
      - REDIS_URL=redis://redis:6379/2
      - TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}
    depends_on:
      - redis
    restart: unless-stopped

  # === PYTHON SERVICES ===
  bot:
    build: ./services/bot
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgres://user:pass@postgres:5432/quiz_bot
      - REDIS_URL=redis://redis:6379/1
      - TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}
      - GAME_SERVICE_URL=http://game:8081
      - AI_ENGINE_URL=http://ai-engine:8002
      - SUBSCRIPTION_URL=http://subscription:8003
    depends_on:
      - postgres
      - redis
      - ai-engine
    restart: unless-stopped

  ai-engine:
    build: ./services/ai-engine
    ports:
      - "8002:8002"
    environment:
      - DATABASE_URL=postgres://user:pass@postgres:5432/quiz_bot
      - REDIS_URL=redis://redis:6379/2
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    depends_on:
      - postgres
      - redis
    restart: unless-stopped

  ai-worker:
    build: ./services/ai-engine
    command: celery -A tasks worker --loglevel=info --concurrency=4
    environment:
      - DATABASE_URL=postgres://user:pass@postgres:5432/quiz_bot
      - REDIS_URL=redis://redis:6379/2
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    depends_on:
      - redis
      - postgres
    restart: unless-stopped

  subscription:
    build: ./services/subscription
    ports:
      - "8003:8003"
    environment:
      - DATABASE_URL=postgres://user:pass@postgres:5432/quiz_bot
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - postgres
      - redis
    restart: unless-stopped

  admin-api:
    build: ./services/admin-api
    ports:
      - "8004:8004"
    environment:
      - DATABASE_URL=postgres://user:pass@postgres:5432/quiz_bot
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - postgres
    restart: unless-stopped

  # === INFRASTRUCTURE ===
  postgres:
    image: postgres:16-alpine
    ports:
      - "5432:5432"
    environment:
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=pass
      - POSTGRES_DB=quiz_bot
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:
```

---

## 3. Dockerfile Standartlari

### Go xizmat uchun (multi-stage)

```dockerfile
# Build stage
FROM golang:1.22-alpine AS builder
WORKDIR /app
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 GOOS=linux go build -o /service ./cmd/main.go

# Run stage
FROM alpine:3.19
RUN apk --no-cache add ca-certificates
COPY --from=builder /service /service
EXPOSE 8080
CMD ["/service"]
```

### Python xizmat uchun

```dockerfile
FROM python:3.12-slim
WORKDIR /app

# Dependencies alohida (cache uchun)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Qoidalar

```
✅ Multi-stage build (Go)
✅ Slim/Alpine images (kichik hajm)
✅ requirements.txt / go.mod alohida COPY (layer cache)
✅ Non-root user (security)
✅ Health check endpoint har bir servisda
❌ Root user bilan ishga tushirish
❌ Dev dependencies production image da
❌ Secrets ni Dockerfile ga yozish
```

---

## 4. CI/CD Pipeline

### GitHub Actions

```yaml
# .github/workflows/ci.yml

name: CI

on:
  push:
    branches: [main, dev]
  pull_request:
    branches: [main]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Go lint
        uses: golangci/golangci-lint-action@v4
        with:
          working-directory: services/gateway
      - name: Python lint
        run: |
          pip install ruff black
          ruff check services/bot services/ai-engine
          black --check services/bot services/ai-engine

  test-go:
    runs-on: ubuntu-latest
    needs: lint
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-go@v5
        with:
          go-version: '1.22'
      - run: |
          cd services/gateway && go test ./... -cover
          cd ../game && go test ./... -cover
          cd ../notifier && go test ./... -cover

  test-python:
    runs-on: ubuntu-latest
    needs: lint
    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_DB: test_db
          POSTGRES_USER: test
          POSTGRES_PASSWORD: test
        ports: ['5432:5432']
      redis:
        image: redis:7
        ports: ['6379:6379']
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - run: |
          cd services/ai-engine
          pip install -r requirements.txt -r requirements-test.txt
          pytest tests/ --cov=. --cov-report=term --cov-fail-under=80

  build:
    runs-on: ubuntu-latest
    needs: [test-go, test-python]
    if: github.ref == 'refs/heads/main'
    steps:
      - uses: actions/checkout@v4
      - name: Build and push images
        run: |
          docker build -t registry/quiz-bot-gateway:${{ github.sha }} ./services/gateway
          docker build -t registry/quiz-bot-bot:${{ github.sha }} ./services/bot
          docker build -t registry/quiz-bot-ai:${{ github.sha }} ./services/ai-engine
          docker build -t registry/quiz-bot-game:${{ github.sha }} ./services/game
          docker push registry/quiz-bot-gateway:${{ github.sha }}
          # ... push all

  deploy:
    runs-on: ubuntu-latest
    needs: build
    if: github.ref == 'refs/heads/main'
    steps:
      - name: Deploy to production
        run: |
          # Update docker-compose on server
          ssh deploy@server "cd /app && docker compose pull && docker compose up -d"
```

---

## 5. Branching va Deploy Strategiyasi

```
Git Flow:

main         ─────●────────●────────●──── (production)
                  │                  ↑
dev          ────●┼───●────●───●────┤     (staging)
                 ││   │    │   │    │
feature/     ────┘│───┘    │   │    │
                  │        │   │    │
hotfix/      ─────┘────────┘───┘────┘


Deploy qoidalari:
├── feature/* → dev ga merge → staging avtomatik deploy
├── dev → main ga merge → production avtomatik deploy
├── hotfix/* → main ga to'g'ridan merge → tezkor deploy
└── Har bir deploy → rollback imkoniyati tayyor

Rollback:
├── docker compose ya'ni oldingi image tag ga qaytarish
├── DB migration down (faqat critical holatlarda)
└── Max 5 daqiqa ichida rollback bo'lishi SHART
```

---

## 6. Server Infratuzilmasi

### Minimal boshlang'ich (1000-10000 user)

```
1 ta server:
├── VPS: 4 CPU, 8 GB RAM, 100 GB SSD
├── OS: Ubuntu 22.04 LTS
├── Docker + Docker Compose
├── Nginx (reverse proxy)
├── PostgreSQL (local)
├── Redis (local)
└── Narx: ~$40-60/oy

Yetarli:
├── Gateway x1
├── Bot x2
├── AI Engine x1 + Worker x2
├── Game x1
├── Notifier x1
└── Admin API x1
```

### O'rtacha (10,000-100,000 user)

```
3 ta server:
├── Server 1: Gateway + Bot + Game (compute)
│   └── 4 CPU, 8 GB RAM
├── Server 2: AI Engine + Workers (AI heavy)
│   └── 4 CPU, 16 GB RAM
├── Server 3: PostgreSQL + Redis (data)
│   └── 4 CPU, 16 GB RAM, 200 GB SSD
└── Narx: ~$120-180/oy
```

### Katta (100,000-1,000,000+ user)

```
Kubernetes yoki Docker Swarm:
├── Node pool 1 (compute): 3-5 node
│   └── Gateway x3, Bot x4, Game x2, Notifier x2
├── Node pool 2 (AI): 2-4 node
│   └── AI Engine x4, Worker x8
├── Managed PostgreSQL (DigitalOcean/AWS RDS)
│   └── Primary + Read Replica
├── Managed Redis (Redis Cloud yoki ElastiCache)
│   └── Cluster mode
└── Narx: ~$400-800/oy

Auto-scaling:
├── CPU > 70% → yangi pod/container qo'shish
├── Queue length > 100 → AI worker qo'shish
└── Connections > 80% pool → DB replica qo'shish
```

---

## 7. Monitoring Stack

```
┌─────────────────────────────────────────────────┐
│                Grafana Dashboard                 │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐     │
│  │ Requests │  │ Errors   │  │ Latency  │     │
│  │  /sec    │  │  rate    │  │  p95     │     │
│  └──────────┘  └──────────┘  └──────────┘     │
└──────────────────────┬──────────────────────────┘
                       │
              ┌────────┴────────┐
              │   Prometheus    │  ← metrikalar yig'ish
              └────────┬────────┘
                       │
    ┌─────────┬────────┼────────┬──────────┐
    ▼         ▼        ▼        ▼          ▼
┌───────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌────────┐
│Gateway│ │ Bot  │ │ Game │ │AI Eng│ │Notifier│
│/metrics│ │/metrics│ │/metrics│/metrics│ │/metrics│
└───────┘ └──────┘ └──────┘ └──────┘ └────────┘


Qo'shimcha:
├── Loki → log yig'ish (grep o'rniga)
├── Alertmanager → xabar yuborish (Telegram guruhga)
└── Uptime Kuma → servislar online/offline
```

### Alertlar

```
CRITICAL (darhol xabar):
├── Xizmat 30+ soniya javob bermaydi
├── Error rate > 10%
├── DB disk 90%+ to'ldi
├── Payment gateway ishlamaydi
└── Telegram API reject rate > 50%

WARNING (5 daqiqa ichida):
├── Response time > 1 sekund (p95)
├── Queue length > 500 (AI tasks)
├── Memory > 80%
├── CPU > 80% (5 daqiqa davomida)
└── SSL sertifikat 7 kundan kam qoldi

INFO (kunlik hisobot):
├── Yangi userlar soni
├── Quiz o'ynalgan soni
├── AI processing o'rtacha vaqt
├── Revenue
└── Error summary
```

---

## 8. Backup va Disaster Recovery

```
PostgreSQL Backup:
├── Har kuni 03:00 da full backup (pg_dump)
├── WAL archiving (point-in-time recovery)
├── Backup saqlash: 30 kun
├── Backup joylar: local + S3 (yoki DO Spaces)
└── Har haftada restore test qilish

Redis:
├── RDB snapshot har 1 soatda
├── AOF persistence (1 sekund)
└── Critical emas — cache qayta quriladi

Disaster Recovery Plan:
├── RTO (Recovery Time Objective): < 30 daqiqa
├── RPO (Recovery Point Objective): < 5 daqiqa
├── Backup serverda Docker Compose tayyor
└── DNS o'zgartirish: < 5 daqiqa (Cloudflare)
```

---

## 9. Security

```
Network:
├── Cloudflare WAF (DDoS, SQL injection himoya)
├── Nginx rate limiting (IP bo'yicha)
├── Internal network (xizmatlar tashqaridan ochiq emas)
├── SSH key-only (parol bilan kira olmaydi)
└── Firewall: faqat 80, 443 ochiq

Application:
├── .env fayllar git da emas (.gitignore)
├── Secrets: Docker secrets yoki Vault
├── Input validation har bir endpoint da
├── SQL injection: ORM ishlatish (SQLAlchemy, GORM)
├── Bot token: environment variable
└���─ API key rotation: har 90 kunda

Database:
├── Alohida user har bir xizmat uchun (minimal privileges)
├── Connection TLS bilan
├── Backup encrypted
└── pgBouncer (connection pooling + DoS himoya)
```

---

## 10. Logging Standarti

```
Format: JSON (structured logging)

{
  "timestamp": "2026-05-16T10:30:00Z",
  "level": "error",
  "service": "ai-engine",
  "request_id": "uuid",
  "user_id": "uuid",
  "message": "OpenAI API timeout",
  "duration_ms": 30000,
  "error": "context deadline exceeded"
}

Level qoidalari:
├── DEBUG: development da, production da o'chirilgan
├── INFO: muhim hodisalar (user ro'yxat, quiz yaratildi, to'lov)
├── WARN: kutilmagan holat, lekin xizmat ishlayapti
├── ERROR: xatolik, user ta'sirlangan
└── FATAL: xizmat to'xtadi, restart kerak

Qoida:
├── Sensitive ma'lumot LOG QILMA (token, parol, to'lov karta)
├── Har bir request uchun request_id (tracing)
├── User harakatlari user_id bilan
└── Performance: duration_ms har doim
```

---

## 11. Health Checks

```
Har bir xizmatda /health endpoint:

GET /health
Response:
{
  "status": "healthy",        -- healthy, degraded, unhealthy
  "service": "ai-engine",
  "version": "1.2.3",
  "uptime_seconds": 86400,
  "checks": {
    "database": "ok",
    "redis": "ok",
    "openai": "ok"
  }
}

Docker health check:
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
  interval: 30s
  timeout: 5s
  retries: 3
  start_period: 10s
```

---

## 12. .env.example

```bash
# === REQUIRED ===
TELEGRAM_BOT_TOKEN=your_bot_token_here
OPENAI_API_KEY=sk-your-key-here
DATABASE_URL=postgres://user:password@localhost:5432/quiz_bot
REDIS_URL=redis://localhost:6379/0

# === PAYMENTS ===
PAYME_MERCHANT_ID=
PAYME_KEY=
CLICK_MERCHANT_ID=
CLICK_SERVICE_ID=
CLICK_SECRET_KEY=
STRIPE_SECRET_KEY=

# === SERVICES (internal) ===
GATEWAY_PORT=8080
BOT_PORT=8000
GAME_PORT=8081
AI_ENGINE_PORT=8002
SUBSCRIPTION_PORT=8003
ADMIN_API_PORT=8004

# === OPTIONAL ===
LOG_LEVEL=info
ENVIRONMENT=development
SENTRY_DSN=
CORS_ORIGINS=http://localhost:3000
```

---

## 13. Deploy Checklist

```
Production ga deploy qilishdan oldin:

□ Barcha testlar o'tdi (CI green)
□ Docker image lar build bo'ldi
□ DB migration tayyor va test qilindi
□ .env production values to'g'ri
□ Health check ishlayapti
□ Monitoring dashboard ko'rinmoqda
□ Backup oxirgi muvaffaqiyatli backup < 24 soat
□ Rollback plan tayyor
□ Team xabardor qilindi
□ Traffic sekin oshiriladi (canary deploy)
```

---

## 14. Scaling Strategiyasi

```
Qachon scale qilish:

                    Hozir        10K user     100K user    1M user
                    ─────        ────────     ─────────    ───────
Gateway             x1           x2           x3           x5
Bot                 x2           x3           x4           x8
Game                x1           x1           x2           x4
AI Engine           x1           x2           x4           x8
AI Worker           x2           x4           x8           x16
Notifier            x1           x1           x2           x4
PostgreSQL          1 node       1 + replica  1 + 2 rep    Cluster
Redis               1 node       1 node       Cluster      Cluster

Auto-scale trigger:
├── CPU > 70% (3 daqiqa) → +1 instance
├── Memory > 80% → +1 instance
├── AI Queue > 200 tasks → +2 workers
└── Response time > 500ms (p95) → +1 gateway
```
