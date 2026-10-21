package analyze

import "testing"

func TestTeamCityAndWerckerCIEntrypoints(t *testing.T) {
	for _, tc := range []struct {
		path string
		want bool
	}{
		{".teamcity/settings.kts", true},
		{"wercker.yml", true},
		{".teamcity/settings.kts.bak", false},
		{".teamcity/settings.kt", false},
		{".teamcity/nested/settings.kts", false},
		{"services/api/.teamcity/settings.kts", false},
		{"wercker.yml.disabled", false},
		{"wercker.yaml", false},
		{"services/api/wercker.yml", false},
	} {
		t.Run(tc.path, func(t *testing.T) {
			if got := isCIConfig(tc.path); got != tc.want {
				t.Fatalf("isCIConfig(%q) = %t, want %t", tc.path, got, tc.want)
			}
		})
	}
}
