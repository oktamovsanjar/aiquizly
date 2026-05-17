package config

import "os"

type Config struct {
	Port        string
	DatabaseURL string
	RedisURL    string
	LogLevel    string
}

func Load() *Config {
	return &Config{
		Port:        getEnv("GAME_PORT", "8081"),
		DatabaseURL: mustEnv("DATABASE_URL"),
		RedisURL:    getEnv("REDIS_URL", "redis://localhost:6379/0"),
		LogLevel:    getEnv("LOG_LEVEL", "info"),
	}
}

func getEnv(key, defaultVal string) string {
	if val := os.Getenv(key); val != "" {
		return val
	}
	return defaultVal
}

func mustEnv(key string) string {
	val := os.Getenv(key)
	if val == "" {
		panic("muhim environment variable yo'q: " + key)
	}
	return val
}
