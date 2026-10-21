package dockercheck

import "testing"

func TestDockerVersionSeparators(t *testing.T) {
	for _, tc := range []struct {
		version string
		valid   bool
	}{
		{"27.1.0", true},
		{"28.0.0+azure", true},
		{"25.0.0-rc.1", true},
		{"1.0.0_dev", true},
		{"dev", true},
		{"27.1.0-", false},
		{"27.1.0+", false},
		{"27..1.0", false},
		{"27.-1.0", false},
		{"27.1.0--rc", false},
		{"27.1.0_+foo", false},
		{"v---", false},
	} {
		t.Run(tc.version, func(t *testing.T) {
			if got := validDockerServerVersion(tc.version); got != tc.valid {
				t.Errorf("validDockerServerVersion(%q)=%v, want %v", tc.version, got, tc.valid)
			}
		})
	}
}
