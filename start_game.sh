#!/bin/bash
export DATABASE_URL="postgres://quizly:P1l2a3y4%25@127.0.0.1:5432/quizly_bot"
export REDIS_URL="redis://127.0.0.1:6379/5"
export GAME_PORT=8011
export LOG_LEVEL=info

cd /home/ubuntu/quizly_bot/quiz-bot/services/game
exec ./game_server
