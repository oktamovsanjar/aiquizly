#!/bin/bash
set -a
source /home/ubuntu/quizly_bot/quiz-bot/.env
set +a

export DATABASE_URL="postgresql+asyncpg://quizly:P1l2a3y4%25@127.0.0.1:5432/quizly_bot"
export REDIS_URL="redis://127.0.0.1:6379/3"
export ADMIN_API_PORT=8014
export ADMIN_SECRET="P1l2a3y4%"
export PYTHONPATH=/home/ubuntu/quizly_bot/quiz-bot/services/admin-api

cd /home/ubuntu/quizly_bot/quiz-bot/services/admin-api
exec ./venv/bin/python -m uvicorn main:app --host 0.0.0.0 --port $ADMIN_API_PORT --log-level info
