package streak

import "testing"

func TestShouldAwardStreakBonus_NoBonus(t *testing.T) {
	cases := []int{1, 2, 3, 6, 8, 13, 15, 29}
	for _, days := range cases {
		if bonus := ShouldAwardStreakBonus(days); bonus != 0 {
			t.Errorf("streak %d uchun 0 XP kutilgan, lekin %d keldi", days, bonus)
		}
	}
}

func TestShouldAwardStreakBonus_7Days(t *testing.T) {
	if bonus := ShouldAwardStreakBonus(7); bonus != 25 {
		t.Errorf("7 kunlik streak uchun 25 XP kutilgan, lekin %d keldi", bonus)
	}
	if bonus := ShouldAwardStreakBonus(14); bonus != 50 {
		t.Errorf("14 kunlik streak uchun 50 XP kutilgan, lekin %d keldi", bonus)
	}
}

func TestShouldAwardStreakBonus_30Days(t *testing.T) {
	if bonus := ShouldAwardStreakBonus(30); bonus != 100 {
		t.Errorf("30 kunlik streak uchun 100 XP kutilgan, lekin %d keldi", bonus)
	}
	if bonus := ShouldAwardStreakBonus(60); bonus != 100 {
		t.Errorf("60 kunlik streak uchun 100 XP kutilgan, lekin %d keldi", bonus)
	}
}

func TestShouldAwardStreakBonus_21Days(t *testing.T) {
	// 21 = 3×7, 7-kunlik milestone
	if bonus := ShouldAwardStreakBonus(21); bonus != 25 {
		t.Errorf("21 kunlik streak uchun 25 XP kutilgan, lekin %d keldi", bonus)
	}
}
