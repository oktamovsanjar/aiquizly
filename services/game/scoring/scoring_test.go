package scoring

import "testing"

// ─── CalculateXP testlari (yangi formula) ────────────────────────────

func TestCalculateXP_PerfectScore20q(t *testing.T) {
	// 20q mukammal, 5 streak, normal vaqt (5s = 5000ms)
	xp := CalculateXP(20, 20, 5, 5000)
	// base=100, perfect=50, speed=20, acc_mult=1.5x => scaled=255, streak=15
	// total = 255 + 15 = 270
	if xp < 250 || xp > 290 {
		t.Errorf("20q mukammal+5streak uchun ~270 XP kutilgan, lekin %d keldi", xp)
	}
}

func TestCalculateXP_Scales(t *testing.T) {
	// 5q mukammal vs 20q mukammal — katta farq bo'lishi kerak
	xp5 := CalculateXP(5, 5, 0, 5000)
	xp20 := CalculateXP(20, 20, 0, 5000)
	if xp20 < xp5*2 {
		t.Errorf("20q mukammal 5q mukammal dan ~3x katta bo'lishi kerak: 5q=%d, 20q=%d", xp5, xp20)
	}
}

func TestCalculateXP_NoNegative(t *testing.T) {
	xp := CalculateXP(0, 20, 0, 0)
	if xp < 0 {
		t.Errorf("XP manfiy bo'lmasligi kerak, lekin %d keldi", xp)
	}
}

func TestCalculateXP_InvalidInput(t *testing.T) {
	xp := CalculateXP(-1, 20, 0, 0)
	if xp != 0 {
		t.Errorf("noto'g'ri input uchun 0 kutilgan, lekin %d keldi", xp)
	}
}

func TestCalculateXP_SpeedBonusOnlyInWindow(t *testing.T) {
	// Juda tez (1000ms) — speed bonus yo'q
	fast := CalculateXP(10, 10, 0, 1000)
	// Normal vaqt (5000ms) — speed bonus bor
	normal := CalculateXP(10, 10, 0, 5000)
	// Juda sekin (15000ms) — speed bonus yo'q
	slow := CalculateXP(10, 10, 0, 15000)
	if normal <= fast || normal <= slow {
		t.Errorf("Normal vaqt eng yuqori XP berishi kerak: fast=%d, normal=%d, slow=%d", fast, normal, slow)
	}
}

func TestCalculateXP_StreakCappedAt30(t *testing.T) {
	xp30 := CalculateXP(10, 10, 30, 5000)
	xp50 := CalculateXP(10, 10, 50, 5000)
	if xp30 != xp50 {
		t.Errorf("Streak 30+ kun XP ga ta'sir qilmasligi kerak: 30=%d, 50=%d", xp30, xp50)
	}
}

func TestCalculateXP_LowAccuracyNoMultiplier(t *testing.T) {
	// 30% to'g'ri (3/10) — multiplier 1.0x
	xp := CalculateXP(3, 10, 0, 5000)
	// base=15, perfect=0, speed=3, acc_mult=1.0 => 18
	if xp < 15 || xp > 25 {
		t.Errorf("Past aniqlik uchun ~18 XP kutilgan, lekin %d keldi", xp)
	}
}

// ─── CalculateXPDetail testlari ──────────────────────────────────────

func TestCalculateXPDetail_PerfectBreakdown(t *testing.T) {
	r := CalculateXPDetail(20, 20, 7, 5000)
	if r.Base == 0 {
		t.Errorf("Base XP > 0 bo'lishi kerak: %+v", r)
	}
	if r.Perfect == 0 {
		t.Errorf("Perfect XP > 0 bo'lishi kerak (mukammal): %+v", r)
	}
	if r.Speed == 0 {
		t.Errorf("Speed XP > 0 bo'lishi kerak (5s vaqt): %+v", r)
	}
	if r.Streak != 7*3 {
		t.Errorf("Streak XP %d kutilgan (21), lekin %d keldi", 7*3, r.Streak)
	}
	if r.Total != r.Base+r.Perfect+r.Speed+r.Streak {
		t.Errorf("Total breakdown yig'indisiga teng bo'lishi kerak: %+v", r)
	}
}

func TestCalculateXPDetail_NotPerfect(t *testing.T) {
	r := CalculateXPDetail(15, 20, 0, 5000)
	if r.Perfect != 0 {
		t.Errorf("Mukammal emas — Perfect=0 bo'lishi kerak, lekin %d", r.Perfect)
	}
}

// ─── CalculateScore testlari ─────────────────────────────────────────

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

// ─── 100-levelli tizim testlari ──────────────────────────────────────

func TestXPForLevel_Monotonic(t *testing.T) {
	// XPForLevel monoton o'sishi kerak
	prev := 0
	for lvl := 1; lvl <= 100; lvl++ {
		xp := XPForLevel(lvl)
		if xp < prev {
			t.Errorf("Lvl %d XP (%d) oldingi (%d) dan past", lvl, xp, prev)
		}
		prev = xp
	}
}

func TestXPForLevel_Boundaries(t *testing.T) {
	if XPForLevel(1) != 0 {
		t.Errorf("Lvl 1 = 0 XP kutilgan, lekin %d", XPForLevel(1))
	}
	// 50 * 2^1.7 ≈ 162
	if XPForLevel(2) < 140 || XPForLevel(2) > 180 {
		t.Errorf("Lvl 2 ~162 XP kutilgan, lekin %d", XPForLevel(2))
	}
	// 50 * 100^1.7 ≈ 125594
	x100 := XPForLevel(100)
	if x100 < 100000 || x100 > 150000 {
		t.Errorf("Lvl 100 ~125k XP kutilgan, lekin %d", x100)
	}
}

func TestDetermineLevelNum(t *testing.T) {
	// Formula bilan har bir level uchun aniq XP hisoblanadi
	// 50 * N^1.7 — DetermineLevelNum(XPForLevel(N)) == N bo'lishi kerak
	cases := []struct {
		xp       int
		minLevel int
		maxLevel int
	}{
		{0, 1, 1},
		{162, 2, 2},        // Lvl 2 boundary
		{2506, 10, 10},     // Lvl 10
		{11898, 25, 25},    // Lvl 25
		{38656, 50, 50},    // Lvl 50
		{125594, 100, 100}, // Lvl 100
		{500000, 100, 100}, // 100+ XP — lvl 100 cap
	}
	for _, c := range cases {
		got := DetermineLevelNum(c.xp)
		if got < c.minLevel || got > c.maxLevel {
			t.Errorf("XP=%d uchun Lvl %d..%d kutilgan, lekin %d", c.xp, c.minLevel, c.maxLevel, got)
		}
	}
}

func TestDetermineLevelNum_Roundtrip(t *testing.T) {
	// XPForLevel(N) -> DetermineLevelNum -> N bo'lishi kerak
	for lvl := 1; lvl <= 100; lvl++ {
		xp := XPForLevel(lvl)
		got := DetermineLevelNum(xp)
		if got != lvl {
			t.Errorf("Lvl %d XP=%d -> DetermineLevelNum=%d", lvl, xp, got)
		}
	}
}

func TestLevelTier(t *testing.T) {
	cases := []struct {
		lvl  int
		tier string
	}{
		{1, "beginner"},
		{10, "beginner"},
		{11, "student"},
		{20, "student"},
		{25, "expert"},
		{50, "experienced"},
		{65, "sage"},
		{75, "professor"},
		{99, "legendary"},
		{100, "legend"},
	}
	for _, c := range cases {
		got := LevelTier(c.lvl)
		if got != c.tier {
			t.Errorf("Lvl %d uchun %q kutilgan, lekin %q", c.lvl, c.tier, got)
		}
	}
}

func TestLevelProgress(t *testing.T) {
	// Lvl 25 ning aynan boshida — ratio ~0
	xp25 := XPForLevel(25)
	level, _, _, ratio := LevelProgress(xp25)
	if level != 25 {
		t.Errorf("XP=%d (Lvl 25 boshi) uchun Lvl 25 kutilgan, lekin %d", xp25, level)
	}
	if ratio > 0.05 {
		t.Errorf("Lvl 25 boshida ratio ~0 kutilgan, lekin %.2f", ratio)
	}

	// Lvl 100 da
	level, _, needed, ratio := LevelProgress(200000)
	if level != 100 {
		t.Errorf("XP=200000 uchun Lvl 100 kutilgan, lekin %d", level)
	}
	if needed != 0 || ratio != 1.0 {
		t.Errorf("Lvl 100 da needed=0, ratio=1.0 kutilgan, lekin needed=%d ratio=%.2f", needed, ratio)
	}
}

func TestDetermineLevel_TierSlug(t *testing.T) {
	// Eski API endi tier slug qaytaradi
	cases := []struct {
		xp   int
		tier string
	}{
		{0, "beginner"},
		{XPForLevel(10), "beginner"},  // Lvl 10 (oxiri)
		{XPForLevel(11), "student"},   // Lvl 11
		{XPForLevel(50), "experienced"},
		{XPForLevel(100), "legend"}, // Lvl 100
	}
	for _, c := range cases {
		got := DetermineLevel(c.xp)
		if got != c.tier {
			t.Errorf("XP=%d uchun tier %q kutilgan, lekin %q", c.xp, c.tier, got)
		}
	}
}
