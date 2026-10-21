package analyze

import "testing"

// Inventory recognizes root-level AppVeyor YAML filename variants.
// Alternate paths are service-side settings and cannot be inferred here.
func TestIsCIConfigAppVeyor(t *testing.T) {
	cases := []struct {
		path string
		want bool
	}{
		{"appveyor.yml", true},
		{".appveyor.yml", true},
		{"appveyor.yaml", true},
		{".appveyor.yaml", true},
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
