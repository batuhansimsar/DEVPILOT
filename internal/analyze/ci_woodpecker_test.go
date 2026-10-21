package analyze

import "testing"

func TestIsCIConfigWoodpecker(t *testing.T) {
	cases := []struct {
		path string
		want bool
	}{
		{path: ".woodpecker.yml", want: true},
		{path: ".woodpecker.yaml", want: true},
		{path: ".woodpecker/build.yml", want: true},
		{path: ".woodpecker/test.yaml", want: true},
		{path: ".woodpecker/", want: false},
		{path: ".woodpecker/README.md", want: false},
		{path: ".woodpecker/nested/build.yml", want: false},
		{path: ".woodpecker/nested/test.yaml", want: false},
		{path: "nested/.woodpecker/build.yml", want: false},
		{path: ".woodpecker.yaml.bak", want: false},
		{path: ".woodpecker/test.yml.old", want: false},
	}
	for _, tc := range cases {
		t.Run(tc.path, func(t *testing.T) {
			if got := isCIConfig(tc.path); got != tc.want {
				t.Errorf("isCIConfig(%q) = %v; want %v", tc.path, got, tc.want)
			}
		})
	}
}
