package analyze

import "testing"

func TestSupplementalInfrastructureSourceLanguages(t *testing.T) {
	cases := []struct {
		name string
		want string
		ok   bool
	}{
		{"main.tf.json", "Terraform", true},
		{"MAIN.TF.JSON", "Terraform", true},
		{"main.tofu", "OpenTofu", true},
		{"main.TOFU.JSON", "OpenTofu", true},
		{"infra/main.bicep", "Bicep", true},
		{"infra/parameters.BICEPPARAM", "Bicep", true},
		{"schemas/schema.cue", "CUE", true},
		{"schema.CUE", "CUE", true},
		{"schema.tf.json.bak", "", false},
		{"main.tofu.json.bak", "", false},
		{"arbitrary.json", "", false},
		{"main.tfvars.json", "", false},
		{"README.md", "", false},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			got, ok := supplementalSourceLanguage(tc.name)
			if got != tc.want || ok != tc.ok {
				t.Fatalf("supplementalSourceLanguage(%q) = (%q, %v), want (%q, %v)", tc.name, got, ok, tc.want, tc.ok)
			}
		})
	}
}

func TestSupplementalExistingLanguagesUnchanged(t *testing.T) {
	for name, want := range map[string]string{
		"notebook.IPYNB": "Jupyter Notebook",
		"api.proto":      "Protocol Buffers",
		"schema.graphql": "GraphQL",
		"shader.Frag":    "GLSL",
		"widget.astro":   "Astro",
		"page.mdx":       "MDX",
	} {
		if got, ok := supplementalSourceLanguage(name); !ok || got != want {
			t.Errorf("supplementalSourceLanguage(%q) = (%q, %v), want (%q, true)", name, got, ok, want)
		}
	}
}
