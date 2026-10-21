package analyze

import "testing"

// Codefresh uses codefresh.yml in the repository root by default. Only the
// actual entrypoint is considered CI, not nested or archived lookalikes.
func TestIsCIConfigCodefresh(t *testing.T) {
	for _, tt := range []struct {
		path string
		want bool
	}{
		{"codefresh.yml", true},
		{"ci/codefresh.yml", false},
		{"nested/codefresh.yml", false},
		{"codefresh.yml.bak", false},
		{"codefresh.yml.example", false},
		{"codefresh.yaml", false},
		{"Codefresh.yml", false},
	} {
		t.Run(tt.path, func(t *testing.T) {
			if got := isCIConfig(tt.path); got != tt.want {
				t.Fatalf("isCIConfig(%q) = %v, want %v", tt.path, got, tt.want)
			}
		})
	}
}
