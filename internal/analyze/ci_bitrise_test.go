package analyze

import "testing"

// Bitrise discovers bitrise.yml from the repository root by default. A custom
// configuration path is a service-side setting and cannot be inferred here.
func TestIsCIConfigBitrise(t *testing.T) {
	cases := []struct {
		path string
		want bool
	}{
		{"bitrise.yml", true},
		{"bitrise.yaml", false},
		{".bitrise.yml", false},
		{"nested/bitrise.yml", false},
		{"bitrise.yml.bak", false},
		{"bitrise.yml.disabled", false},
		{"bitriseyml", false},
	}
	for _, tc := range cases {
		t.Run(tc.path, func(t *testing.T) {
			if got := isCIConfig(tc.path); got != tc.want {
				t.Fatalf("isCIConfig(%q) = %v, want %v", tc.path, got, tc.want)
			}
		})
	}
}
