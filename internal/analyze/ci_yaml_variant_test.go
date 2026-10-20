package analyze

import "testing"

func TestIsCIConfigAdditionalYAMLVariants(t *testing.T) {
	cases := []struct {
		path string
		want bool
	}{
		{"azure-pipelines.yaml", true},
		{".drone.yaml", true},
		{"azure-pipelines.yml", true},
		{".drone.yml", true},
		{"nested/azure-pipelines.yaml", false},
		{"nested/.drone.yaml", false},
		{"azure-pipelines.yaml.bak", false},
		{".drone.yaml.disabled", false},
	}
	for _, tc := range cases {
		t.Run(tc.path, func(t *testing.T) {
			if got := isCIConfig(tc.path); got != tc.want {
				t.Fatalf("isCIConfig(%q) = %v, want %v", tc.path, got, tc.want)
			}
		})
	}
}
