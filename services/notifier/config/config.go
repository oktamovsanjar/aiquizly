package config

import "os"

type Config struct {
	Port     string
	RedisURL string
	BotToken string
	LogLevel string
}

func Load() *Config {
	return &Config{
		Port:     getEnv("NOTIFIER_PORT", "8082"),
		RedisURL: getEnv("REDIS_URL", "redis://localhost:6379/2"),
		BotToken: mustEnv("TELEGRAM_BOT_TOKEN"),
		LogLevel: getEnv("LOG_LEVEL", "info"),
	}
}

func getEnv(key, def string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return def
}

func mustEnv(key string) string {
	v := os.Getenv(key)
	if v == "" {
		panic("muhim env yo'q: " + key)
	}
	return v
}
