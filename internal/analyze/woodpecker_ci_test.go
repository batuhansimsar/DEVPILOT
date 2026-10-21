package analyze

import "testing"

func TestWoodpeckerCIPathVariants(t *testing.T) {
	cases := []struct {
		path string
		want bool
	}{
		{".woodpecker.yml", true},
		{".woodpecker.yaml", true},
		{".woodpecker/build.yml", true},
		{".woodpecker/release.yaml", true},
		{".woodpecker/README.md", false},
		{".woodpecker/build.yml.disabled", false},
		{".woodpecker/nested/build.yml", false},
		{"nested/.woodpecker/build.yaml", false},
		{".woodpecker/", false},
		{".woodpecker.yml.bak", false},
	}
	for _, tc := range cases {
		t.Run(tc.path, func(t *testing.T) {
			if got := isCIConfig(tc.path); got != tc.want {
				t.Fatalf("isCIConfig(%q) = %t, want %t", tc.path, got, tc.want)
			}
		})
	}
}
