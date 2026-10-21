package analyze

import "testing"

// Terraform variable files are part of the source inventory even when no
// .tf file exists. JSON variants and auto-loaded variable files count too.
func TestTerraformVariableSourceFormats(t *testing.T) {
	cases := []struct {
		name, want string
		ok         bool
	}{
		{"terraform.tfvars", "Terraform", true},
		{"terraform.tfvars.json", "Terraform", true},
		{"prod.auto.tfvars", "Terraform", true},
		{"PROD.AUTO.TFVARS.JSON", "Terraform", true},
		{"config.TFVARS", "Terraform", true},
		{"main.tf.json", "Terraform", true},
		{"main.tofu.json", "OpenTofu", true},
		{"main.tfvars.json.bak", "", false},
		{"main.tfvars.bak", "", false},
		{"main.tfvars.json.old", "", false},
		{"file.json", "", false},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			got, ok := supplementalSourceLanguage(tc.name)
			if got != tc.want || ok != tc.ok {
				t.Fatalf("supplementalSourceLanguage(%q) = (%q, %t), want (%q, %t)", tc.name, got, ok, tc.want, tc.ok)
			}
		})
	}
}
