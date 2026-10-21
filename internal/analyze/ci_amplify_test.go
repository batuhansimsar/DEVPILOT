package analyze

import "testing"

func TestAWSAmplifyCIEntrypoint(t *testing.T) {
	for _, tc := range []struct {
		path string
		want bool
	}{
		{"amplify.yml", true},
		{"apps/web/amplify.yml", false},
		{".github/amplify.yml", false},
		{"amplify.yml.bak", false},
		{"amplify.yml.disabled", false},
		{"amplify.yaml", false},
		{"AmPlIfY.yml", false},
	} {
		t.Run(tc.path, func(t *testing.T) {
			if got := isCIConfig(tc.path); got != tc.want {
				t.Errorf("isCIConfig(%q) = %t, want %t", tc.path, got, tc.want)
		})
	}
}
