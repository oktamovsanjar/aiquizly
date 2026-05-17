package scoring

import "testing"

func TestCalculateXP_PerfectScore(t *testing.T) {
	xp := CalculateXP(20, 20, 5)
	expected := BaseXP + PerfectBonusXP + 5*StreakXPPerDay
	if xp != expected {
		t.Errorf("kutilgan %d, lekin %d keldi", expected, xp)
	}
}

func TestCalculateXP_NoNegative(t *testing.T) {
	xp := CalculateXP(0, 20, 0)
	if xp < 0 {
		t.Errorf("XP manfiy bo'lmasligi kerak, lekin %d keldi", xp)
	}
}

func TestCalculateXP_InvalidInput(t *testing.T) {
	xp := CalculateXP(-1, 20, 0)
	if xp != 0 {
		t.Errorf("noto'g'ri input uchun 0 kutilgan, lekin %d keldi", xp)
	}
}

func TestCalculateScore_Full(t *testing.T) {
	score := CalculateScore(20, 20, 0, 30000)
	if score < 800 {
		t.Errorf("100%% to'g'ri uchun min 800 ball kutilgan, lekin %d keldi", score)
	}
}

func TestCalculateScore_Zero(t *testing.T) {
	score := CalculateScore(0, 0, 0, 0)
	if score != 0 {
		t.Errorf("0 savol uchun 0 ball kutilgan, lekin %d keldi", score)
	}
}

func TestDetermineLevel(t *testing.T) {
	cases := []struct {
		xp       int
		expected string
	}{
		{0, "beginner"},
		{100, "beginner"},
		{101, "learner"},
		{500, "learner"},
		{501, "expert"},
		{2001, "master"},
		{5001, "professor"},
		{15001, "academic"},
	}

	for _, c := range cases {
		got := DetermineLevel(c.xp)
		if got != c.expected {
			t.Errorf("XP=%d uchun %q kutilgan, lekin %q keldi", c.xp, c.expected, got)
		}
	}
}
