package achievement

import (
	"context"
	"testing"

	"github.com/google/uuid"
	"github.com/quiz-bot/game/db"
)

// achievementCondition larni to'g'ridan to'g'ri test qilamiz (DB mock siz)

func statsWithGames(n int) *db.UserStats {
	return &db.UserStats{TotalGames: n, CurrentStreak: 0, TotalCorrect: 0, TotalWrong: 0, Level: "beginner"}
}

func statsWithStreak(n int) *db.UserStats {
	return &db.UserStats{TotalGames: 1, CurrentStreak: n, TotalCorrect: 0, TotalWrong: 0, Level: "beginner"}
}

func statsWithAnswers(n int) *db.UserStats {
	return &db.UserStats{TotalGames: n, CurrentStreak: 0, TotalCorrect: n / 2, TotalWrong: n - n/2, Level: "beginner"}
}

func findCondition(slug string) *achievementCondition {
	for i := range conditions {
		if conditions[i].slug == slug {
			return &conditions[i]
		}
	}
	return nil
}

func TestFirstQuizCondition(t *testing.T) {
	cond := findCondition("first_quiz")
	if cond == nil {
		t.Fatal("first_quiz condition topilmadi")
	}

	ctx := context.Background()
	uid := uuid.New()

	// 0 o'yin — shartni bajarmasligi kerak
	met, err := cond.check(ctx, nil, uid, statsWithGames(0), "game_complete")
	if err != nil || met {
		t.Errorf("0 o'yin uchun false kutilgan")
	}

	// 1 o'yin — shartni bajarishi kerak
	met, err = cond.check(ctx, nil, uid, statsWithGames(1), "game_complete")
	if err != nil || !met {
		t.Errorf("1 o'yin uchun true kutilgan")
	}
}

func TestStreakCondition(t *testing.T) {
	cond := findCondition("7_day_streak")
	if cond == nil {
		t.Fatal("7_day_streak condition topilmadi")
	}

	ctx := context.Background()
	uid := uuid.New()

	// 6 kunlik streak — shartni bajarmasligi kerak
	met, _ := cond.check(ctx, nil, uid, statsWithStreak(6), "game_complete")
	if met {
		t.Errorf("6 kunlik streak uchun false kutilgan")
	}

	// 7 kunlik streak — shartni bajarishi kerak
	met, _ = cond.check(ctx, nil, uid, statsWithStreak(7), "game_complete")
	if !met {
		t.Errorf("7 kunlik streak uchun true kutilgan")
	}

	// 30 kunlik streak — ham bajarishi kerak
	met, _ = cond.check(ctx, nil, uid, statsWithStreak(30), "game_complete")
	if !met {
		t.Errorf("30 kunlik streak uchun true kutilgan")
	}
}

func TestPerfectScoreCondition(t *testing.T) {
	cond := findCondition("perfect_score")
	if cond == nil {
		t.Fatal("perfect_score condition topilmadi")
	}

	ctx := context.Background()
	uid := uuid.New()
	stats := statsWithGames(5)

	// Noto'g'ri event — shartni bajarmasligi kerak
	met, _ := cond.check(ctx, nil, uid, stats, "game_complete")
	if met {
		t.Errorf("game_complete event uchun false kutilgan")
	}

	// perfect_score event — shartni bajarishi kerak
	met, _ = cond.check(ctx, nil, uid, stats, "perfect_score")
	if !met {
		t.Errorf("perfect_score event uchun true kutilgan")
	}
}

func TestAcademicLevelCondition(t *testing.T) {
	// Yangi 100-levelli tizimda academic_level = Lvl 100 ga yetish
	cond := findCondition("academic_level")
	if cond == nil {
		t.Fatal("academic_level condition topilmadi")
	}

	ctx := context.Background()
	uid := uuid.New()

	// Past XP — shartni bajarmasligi kerak
	stats := &db.UserStats{TotalXP: 100, Level: "beginner"}
	met, _ := cond.check(ctx, nil, uid, stats, "game_complete")
	if met {
		t.Errorf("100 XP uchun false kutilgan")
	}

	// 200k XP — Lvl 100 ga yetadi, shartni bajarishi kerak
	stats = &db.UserStats{TotalXP: 200000, Level: "legend"}
	met, _ = cond.check(ctx, nil, uid, stats, "game_complete")
	if !met {
		t.Errorf("200k XP (Lvl 100) uchun true kutilgan")
	}
}

func TestLevelMilestonesConditions(t *testing.T) {
	ctx := context.Background()
	uid := uuid.New()

	cases := []struct {
		slug     string
		passXP   int
		failXP   int
	}{
		{"level_10", 5000, 100},
		{"level_25", 15000, 100},
		{"level_50", 50000, 100},
		{"level_75", 100000, 100},
		{"level_100", 200000, 100},
	}
	for _, c := range cases {
		cond := findCondition(c.slug)
		if cond == nil {
			t.Errorf("%s condition topilmadi", c.slug)
			continue
		}
		met, _ := cond.check(ctx, nil, uid, &db.UserStats{TotalXP: c.passXP}, "game_complete")
		if !met {
			t.Errorf("%s: %d XP uchun true kutilgan", c.slug, c.passXP)
		}
		met, _ = cond.check(ctx, nil, uid, &db.UserStats{TotalXP: c.failXP}, "game_complete")
		if met {
			t.Errorf("%s: %d XP uchun false kutilgan", c.slug, c.failXP)
		}
	}
}

func TestStreakLadderConditions(t *testing.T) {
	ctx := context.Background()
	uid := uuid.New()

	cases := []struct {
		slug     string
		passDays int
		failDays int
	}{
		{"streak_3", 3, 2},
		{"streak_14", 14, 13},
		{"streak_30", 30, 29},
		{"streak_100", 100, 99},
	}
	for _, c := range cases {
		cond := findCondition(c.slug)
		if cond == nil {
			t.Errorf("%s condition topilmadi", c.slug)
			continue
		}
		met, _ := cond.check(ctx, nil, uid, statsWithStreak(c.passDays), "game_complete")
		if !met {
			t.Errorf("%s: %d kun uchun true kutilgan", c.slug, c.passDays)
		}
		met, _ = cond.check(ctx, nil, uid, statsWithStreak(c.failDays), "game_complete")
		if met {
			t.Errorf("%s: %d kun uchun false kutilgan", c.slug, c.failDays)
		}
	}
}

func TestGamesLadderConditions(t *testing.T) {
	ctx := context.Background()
	uid := uuid.New()

	cases := []struct {
		slug   string
		passN  int
		failN  int
	}{
		{"games_10", 10, 9},
		{"games_50", 50, 49},
		{"games_100", 100, 99},
		{"games_500", 500, 499},
	}
	for _, c := range cases {
		cond := findCondition(c.slug)
		if cond == nil {
			t.Errorf("%s condition topilmadi", c.slug)
			continue
		}
		met, _ := cond.check(ctx, nil, uid, statsWithGames(c.passN), "game_complete")
		if !met {
			t.Errorf("%s: %d o'yin uchun true kutilgan", c.slug, c.passN)
		}
		met, _ = cond.check(ctx, nil, uid, statsWithGames(c.failN), "game_complete")
		if met {
			t.Errorf("%s: %d o'yin uchun false kutilgan", c.slug, c.failN)
		}
	}
}

func Test1000QuestionsCondition(t *testing.T) {
	cond := findCondition("1000_questions")
	if cond == nil {
		t.Fatal("1000_questions condition topilmadi")
	}

	ctx := context.Background()
	uid := uuid.New()

	// 999 javob — shartni bajarmasligi kerak
	met, _ := cond.check(ctx, nil, uid, statsWithAnswers(999), "game_complete")
	if met {
		t.Errorf("999 javob uchun false kutilgan")
	}

	// 1000 javob — shartni bajarishi kerak
	met, _ = cond.check(ctx, nil, uid, statsWithAnswers(1000), "game_complete")
	if !met {
		t.Errorf("1000 javob uchun true kutilgan")
	}
}
