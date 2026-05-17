package config

import (
	"os"
)

type Config struct {
	Port           string
	RedisURL       string
	BotServiceURL  string
	GameServiceURL string
	BotToken       string
	LogLevel       string
}

func Load() *Config {
	return &Config{
		Port:           getEnv("GATEWAY_PORT", "8080"),
		RedisURL:       getEnv("REDIS_URL", "redis://localhost:6379/0"),
		BotServiceURL:  getEnv("BOT_SERVICE_URL", "http://localhost:8000"),
		GameServiceURL: getEnv("GAME_SERVICE_URL", "http://localhost:8081"),
		BotToken:       getEnv("TELEGRAM_BOT_TOKEN", ""),
		LogLevel:       getEnv("LOG_LEVEL", "info"),
	}
}

func getEnv(key, defaultVal string) string {
	if val := os.Getenv(key); val != "" {
		return val
	}
	return defaultVal
}
