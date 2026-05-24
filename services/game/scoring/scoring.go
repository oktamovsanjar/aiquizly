package scoring

import (
	"math"

	"github.com/quiz-bot/game/db"
)

// XP hisoblash konstantalari (Faza 2 - yangi tizim)
const (
	BaseXPPerCorrect = 5    // 1 to'g'ri javob uchun
	PerfectBonusBase = 10   // mukammal natija uchun bazoviy bonus
	PerfectBonusPerQ = 2    // har bir savol uchun mukammal bonus
	SpeedBonusPerQ   = 1    // tezlik bonusi (har to'g'ri javob)
	StreakXPPerDay   = 3    // streak XP har kun
	StreakXPCapDays  = 30   // streak XP shu sondan keyin to'xtaydi
	SpeedMinMs       = 1500 // tezlik bonusi uchun min vaqt (anti-cheat)
	SpeedMaxMs       = 8000 // tezlik bonusi uchun max vaqt
	// Eski konstantalar — backward compat uchun (eski xp_logs reconstructions)
	BaseXP         = 10
	PerfectBonusXP = 25
)

// XPCalcResult — XP hisobining batafsil natijasi (UI da breakdown ko'rsatish uchun)
type XPCalcResult struct {
	Base    int // correct * 5 ga teng (acc multipliersiz)
	Perfect int // perfect bonus
	Speed   int // tezlik bonusi
	Streak  int // streak XP (kunlar bo'yicha)
	Total   int // jami (multiplier bilan)
}

// CalculateXPDetail — yangi formula bilan XP ni hisoblaydi va breakdown qaytaradi
//
// Parametrlar:
//   - correct: to'g'ri javoblar soni
//   - total: jami savollar
//   - streakDays: joriy streak
//   - avgMsPerQ: o'rtacha savol uchun vaqt (ms). 0 bo'lsa speed bonus yo'q.
//
// Formula:
//
//	base       = correct * 5
//	perfect    = (correct == total && total >= 3) ? (10 + total*2) : 0
//	speed      = (1500 <= avgMs <= 8000) ? correct * 1 : 0
//	acc_mult   = (acc < 0.5) ? 1.0 : (1.0 + (acc - 0.5))   // 100% = 1.5x
//	streak     = min(streakDays, 30) * 3
//	total      = round(acc_mult * (base + perfect + speed)) + streak
func CalculateXPDetail(correct, total, streakDays int, avgMsPerQ int) XPCalcResult {
	if correct < 0 || total <= 0 {
		return XPCalcResult{}
	}
	if correct > total {
		correct = total
	}

	base := correct * BaseXPPerCorrect

	perfect := 0
	if correct == total && total >= 3 {
		perfect = PerfectBonusBase + total*PerfectBonusPerQ
	}

	speed := 0
	if avgMsPerQ >= SpeedMinMs && avgMsPerQ <= SpeedMaxMs {
		speed = correct * SpeedBonusPerQ
	}

	acc := float64(correct) / float64(total)
	accMult := 1.0
	if acc >= 0.5 {
		accMult = 1.0 + (acc - 0.5)
	}

	scaled := int(math.Round(accMult * float64(base+perfect+speed)))

	streakXP := streakDays
	if streakXP > StreakXPCapDays {
		streakXP = StreakXPCapDays
	}
	if streakXP < 0 {
		streakXP = 0
	}
	streakXP = streakXP * StreakXPPerDay

	// Multiplier ni breakdown ga proportional taqsimlaymiz
	scaledBase := int(math.Round(accMult * float64(base)))
	scaledPerfect := int(math.Round(accMult * float64(perfect)))
	scaledSpeed := scaled - scaledBase - scaledPerfect
	if scaledSpeed < 0 {
		scaledSpeed = 0
	}

	return XPCalcResult{
		Base:    scaledBase,
		Perfect: scaledPerfect,
		Speed:   scaledSpeed,
		Streak:  streakXP,
		Total:   scaled + streakXP,
	}
}

// CalculateXP — yangi formula (Faza 2). Faqat jami XP ni qaytaradi.
// Breakdown kerak bo'lsa CalculateXPDetail ishlatiladi.
func CalculateXP(correct, total, streakDays int, avgMsPerQ int) int {
	return CalculateXPDetail(correct, total, streakDays, avgMsPerQ).Total
}

// CalculateScore — quiz ballini hisoblaydi (0-1000) — o'zgarmagan
func CalculateScore(correct, total int, timeSpentMs int64, timeLimitMs int64) int {
	if total == 0 {
		return 0
	}

	accuracy := float64(correct) / float64(total)
	baseScore := int(accuracy * 800)

	if timeLimitMs > 0 && timeSpentMs < timeLimitMs {
		timeBonus := int(float64(timeLimitMs-timeSpentMs) / float64(timeLimitMs) * 200)
		baseScore += timeBonus
	}

	return baseScore
}

// XPForLevel — N-darajaga yetish uchun zarur jami XP
// Formula: 50 * N^1.7 (kvadratik o'sish, 100 ga yetib ~170k XP)
func XPForLevel(level int) int {
	if level <= 1 {
		return 0
	}
	if level > 100 {
		level = 100
	}
	return int(math.Round(50.0 * math.Pow(float64(level), 1.7)))
}

// DetermineLevelNum — totalXP dan 1..100 darajani aniqlaydi (binary search)
func DetermineLevelNum(totalXP int) int {
	if totalXP < 0 {
		return 1
	}
	lo, hi := 1, 100
	for lo < hi {
		mid := (lo + hi + 1) / 2
		if XPForLevel(mid) <= totalXP {
			lo = mid
		} else {
			hi = mid - 1
		}
	}
	return lo
}

// LevelTier — daraja raqamidan tier slugini qaytaradi
func LevelTier(level int) string {
	switch {
	case level <= 10:
		return "beginner"
	case level <= 20:
		return "student"
	case level <= 30:
		return "expert"
	case level <= 40:
		return "skilled"
	case level <= 50:
		return "experienced"
	case level <= 60:
		return "mentor"
	case level <= 70:
		return "sage"
	case level <= 80:
		return "professor"
	case level <= 90:
		return "academic"
	case level <= 99:
		return "legendary"
	default:
		return "legend"
	}
}

// LevelProgress — joriy daraja ichidagi progress
func LevelProgress(totalXP int) (level, currentXP, neededXP int, ratio float64) {
	level = DetermineLevelNum(totalXP)
	base := XPForLevel(level)
	if level >= 100 {
		return 100, 0, 0, 1.0
	}
	next := XPForLevel(level + 1)
	currentXP = totalXP - base
	neededXP = next - base
	if neededXP <= 0 {
		return level, 0, 0, 1.0
	}
	ratio = float64(currentXP) / float64(neededXP)
	if ratio < 0 {
		ratio = 0
	}
	if ratio > 1 {
		ratio = 1
	}
	return
}

// DetermineLevel — eski string daraja (tier slug) — backward compat
// Endi tier slugini qaytaradi: beginner/student/expert/skilled/experienced/mentor/sage/professor/academic/legendary/legend
func DetermineLevel(totalXP int) string {
	return LevelTier(DetermineLevelNum(totalXP))
}

// CheckAchievements — eski API uchun (slug ro'yxati qaytaradi)
// Faza 4 da achievement/checker.go ga ko'chiriladi, hozircha qoldirildi
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

	if DetermineLevelNum(stats.TotalXP) >= 100 {
		slugs = append(slugs, "academic_level")
	}

	return slugs
}
