package analyze

import "testing"

func TestIsCIConfigCloudProviders(t *testing.T) {
	tests := []struct {
		path string
		want bool
	}{
		{"appveyor.yml", true},
		{".appveyor.yml", true},
		{".appveyor.yaml", true},
		{"appveyor.yaml", true},
		{"buildspec.yml", true},
		{"buildspec.yaml", true},
		{"cloudbuild.yml", true},
		{"cloudbuild.yaml", true},
		{"cloudbuild.json", true},
		{".semaphore/semaphore.yml", true},
		{".semaphore/semaphore.yaml", true},
		{"services/api/buildspec.yml", false},
		{"nested/cloudbuild.yaml", false},
		{"nested/appveyor.yml", false},
		{".semaphore/README.yml", false},
		{".semaphore/archive/semaphore.yaml", false},
		{".semaphore/semaphore.yml.bak", false},
		{"buildspec.yml.disabled", false},
		{"cloudbuild.yaml.bak", false},
		{"appveyor.yaml~", false},
	}
	for _, tt := range tests {
		t.Run(tt.path, func(t *testing.T) {
			if got := isCIConfig(tt.path); got != tt.want {
				t.Errorf("isCIConfig(%q) = %t, want %t", tt.path, got, tt.want)
			}
		})
	}
}
