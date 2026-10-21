package analyze

import "testing"

// AppVeyor supports both root-level appveyor.yml and .appveyor.yml files.
// Alternate paths are service-side settings and cannot be inferred here.
func TestIsCIConfigAppVeyor(t *testing.T) {
	cases := []struct {
		path string
		want bool
	}{
		{"appveyor.yml", true},
		{".appveyor.yml", true},
		{"appveyor.yaml", false},
		{".appveyor.yaml", false},
		{"src/appveyor.yml", false},
		{"src/.appveyor.yml", false},
		{"appveyor.yml.bak", false},
		{".appveyor.yml.disabled", false},
	}
	for _, tc := range cases {
		t.Run(tc.path, func(t *testing.T) {
			if got := isCIConfig(tc.path); got != tc.want {
				t.Fatalf("isCIConfig(%q) = %v, want %v", tc.path, got, tc.want)
			}
		})
	}
}
