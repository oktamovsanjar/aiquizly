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
	cond := findCondition("academic_level")
	if cond == nil {
		t.Fatal("academic_level condition topilmadi")
	}

	ctx := context.Background()
	uid := uuid.New()

	// Beginner level — shartni bajarmasligi kerak
	stats := &db.UserStats{Level: "beginner"}
	met, _ := cond.check(ctx, nil, uid, stats, "game_complete")
	if met {
		t.Errorf("beginner level uchun false kutilgan")
	}

	// Academic level — shartni bajarishi kerak
	stats = &db.UserStats{Level: "academic"}
	met, _ = cond.check(ctx, nil, uid, stats, "game_complete")
	if !met {
		t.Errorf("academic level uchun true kutilgan")
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
