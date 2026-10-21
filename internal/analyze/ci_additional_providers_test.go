package analyze

import "testing"

func TestAdditionalCIProviderEntrypoints(t *testing.T) {
	for _, tc := range []struct {
		path string
		want bool
	}{
		{".semaphore/semaphore.yml", true},
		{".semaphore/semaphore.yaml", true},
		{".cirrus.yml", true},
		{"buildspec.yml", true},
		{".semaphore/extra.yml", false},
		{".semaphore/nested/semaphore.yml", false},
		{"service/.semaphore/semaphore.yml", false},
		{"service/.cirrus.yml", false},
		{"service/buildspec.yml", false},
		{".cirrus.yaml", false},
		{"buildspec.yaml", true},
		{"buildspec.yml.bak", false},
		{".cirrus.yml.disabled", false},
	} {
		t.Run(tc.path, func(t *testing.T) {
			if got := isCIConfig(tc.path); got != tc.want {
				t.Fatalf("isCIConfig(%q) = %t, want %t", tc.path, got, tc.want)
			}
		})
	}
}
