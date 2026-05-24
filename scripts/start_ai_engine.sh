#!/bin/bash
set -a
source /home/ubuntu/quizly_bot/quiz-bot/.env
set +a

export DATABASE_URL="postgresql+asyncpg://quizly:P1l2a3y4%25@127.0.0.1:5432/quizly_bot"
export REDIS_URL="redis://127.0.0.1:6379/4"
export AI_ENGINE_PORT=8012

cd /home/ubuntu/quizly_bot/quiz-bot/services/ai-engine
export PYTHONPATH=/home/ubuntu/quizly_bot/quiz-bot/services/ai-engine
exec ./venv/bin/python -m uvicorn main:app --host 0.0.0.0 --port $AI_ENGINE_PORT --log-level info
