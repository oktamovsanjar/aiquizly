package scoring

import "github.com/quiz-bot/game/db"

// XP hisoblash konstantalari
const (
	BaseXP         = 10
	PerfectBonusXP = 25
	StreakXPPerDay = 5
)

// CalculateXP — quiz natijasi bo'yicha XP hisoblaydi
func CalculateXP(correct, total, streakDays int) int {
	if correct < 0 || total <= 0 {
		return 0
	}

	xp := BaseXP

	// 100% to'g'ri bo'lsa bonus
	if correct == total {
		xp += PerfectBonusXP
	}

	// Streak bonus
	xp += streakDays * StreakXPPerDay

	return xp
}

// CalculateScore — quiz ballini hisoblaydi (0-1000)
func CalculateScore(correct, total int, timeSpentMs int64, timeLimitMs int64) int {
	if total == 0 {
		return 0
	}

	// Asosiy ball: to'g'ri javoblar ulushi * 800
	accuracy := float64(correct) / float64(total)
	baseScore := int(accuracy * 800)

	// Vaqt bonusi: tez javob bersa qo'shimcha ball (max 200)
	if timeLimitMs > 0 && timeSpentMs < timeLimitMs {
		timeBonus := int(float64(timeLimitMs-timeSpentMs) / float64(timeLimitMs) * 200)
		baseScore += timeBonus
	}

	return baseScore
}

// DetermineLevel — XP ga qarab foydalanuvchi darajasini aniqlaydi
func DetermineLevel(totalXP int) string {
	switch {
	case totalXP >= 15001:
		return "academic"
	case totalXP >= 5001:
		return "professor"
	case totalXP >= 2001:
		return "master"
	case totalXP >= 501:
		return "expert"
	case totalXP >= 101:
		return "learner"
	default:
		return "beginner"
	}
}

// CheckAchievements — foydalanuvchi statistikasiga qarab ochilishi kerak bo'lgan
// yutuq slug larini qaytaradi. Sluglar achievement/checker.go da qayta tekshiriladi va DB ga yoziladi.
func CheckAchievements(stats *db.UserStats, games int, streak int) []string {
	var slugs []string

	if games >= 1 {
		slugs = append(slugs, "first_quiz")
	}

	if streak >= 7 {
		slugs = append(slugs, "7_day_streak")
	}

	if stats.TotalCorrect+stats.TotalWrong >= 1000 {
		slugs = append(slugs, "1000_questions")
	}

	if stats.Level == "academic" {
		slugs = append(slugs, "academic_level")
	}

	return slugs
}
