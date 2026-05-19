#!/bin/bash
set -a
source /home/ubuntu/quizly_bot/quiz-bot/.env
set +a

export DATABASE_URL="postgresql+asyncpg://quizly:P1l2a3y4%25@127.0.0.1:5432/quizly_bot"
export REDIS_URL="redis://127.0.0.1:6379/3"
export BOT_PORT=8010
export WEBHOOK_URL="https://aiquizly.uzbek-talim.uz"
export AI_ENGINE_URL="http://127.0.0.1:8012"
export GAME_SERVICE_URL="http://127.0.0.1:8011"
export SUBSCRIPTION_URL="http://127.0.0.1:8013"
export NOTIFIER_URL="http://127.0.0.1:8015"

cd /home/ubuntu/quizly_bot/quiz-bot/services/bot
exec ./venv/bin/python main.py
