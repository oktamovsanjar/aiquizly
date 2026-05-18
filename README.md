# AI Quiz Bot

Telegram bot — fayldan AI yordamida avtomatik quiz yaratadi.

## Arxitektura

```
quiz-bot/
├── services/
│   ├── bot/           — Telegram bot (Python, aiogram 3)
│   ├── ai-engine/     — Quiz generatsiya (Python, FastAPI, Celery)
│   ├── game/          — O'yin logikasi (Go)
│   ├── gateway/       — API Gateway (Go)
│   ├── notifier/      — Telegram xabarnomalar (Go)
│   ├── subscription/  — Obuna va limitlar (Python, FastAPI)
│   └── admin-api/     — Admin panel API + frontend (Python, FastAPI)
├── shared/
│   ├── migrations/    — PostgreSQL migratsiyalar
│   └── proto/         — Protobuf ta'riflar
├── infra/
│   ├── nginx/         — Nginx konfiguratsiya
│   ├── postgres/      — DB init skriptlari
│   └── redis/         — Redis konfiguratsiya
├── scripts/           — Deploy va backup skriptlari
├── tests/             — E2E testlar
└── docs/              — Arxitektura, DevOps, DB hujjatlari
```

## Ishga tushirish

```bash
# 1. Environment sozlash
cp .env.example .env
# .env ni to'ldiring (TELEGRAM_BOT_TOKEN, DEEPSEEK_API_KEY va boshqalar)

# 2. Ishga tushirish
docker compose up -d

# 3. Holat tekshirish
docker compose ps
```

## Servislar

| Servis      | Port | Manzil                        |
|-------------|------|-------------------------------|
| Gateway     | 8080 | http://localhost:8080         |
| Bot health  | 8000 | http://localhost:8000/health  |
| AI Engine   | 8002 | http://localhost:8002/docs    |
| Subscription| 8003 | http://localhost:8003/docs    |
| Admin Panel | 8004 | http://localhost:8004         |
| Game        | 8081 | http://localhost:8081/health  |

## Testlar

```bash
# Bot testlari
cd services/bot && pytest tests/unit/ -v

# AI engine testlari
cd services/ai-engine && pytest tests/unit/ -v
```

## Hujjatlar

- [Arxitektura](docs/ARCHITECTURE.md)
- [Bot UX](docs/BOT_UX.md)
- [Ma'lumotlar bazasi](docs/DATABASE.md)
- [DevOps](docs/DEVOPS.md)
- [QA](docs/QA.md)
