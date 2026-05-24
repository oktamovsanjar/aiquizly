#!/bin/bash
set -a
source /home/ubuntu/quizly_bot/quiz-bot/.env
set +a

export DATABASE_URL="postgresql+asyncpg://quizly:P1l2a3y4%25@127.0.0.1:5432/quizly_bot"
export REDIS_URL="redis://127.0.0.1:6379/4"

cd /home/ubuntu/quizly_bot/quiz-bot/services/ai-engine
export PYTHONPATH=/home/ubuntu/quizly_bot/quiz-bot/services/ai-engine
exec ./venv/bin/celery -A tasks.process_file:celery_app worker --loglevel=info --concurrency=2 -n quizly-worker@%h
