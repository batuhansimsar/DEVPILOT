package analyze

import "testing"

func TestExtendedSourceLanguages(t *testing.T) {
	cases := []struct {
		extension string
		language  string
	}{
		{".ps1", "PowerShell"},
		{".psm1", "PowerShell"},
		{".psd1", "PowerShell"},
		{".gd", "GDScript"},
		{".nim", "Nim"},
		{".ml", "OCaml"},
		{".mli", "OCaml"},
		{".typ", "Typst"},
		// Existing language and ambiguous-extension rules must remain intact.
		{".hpp", "C++"},
		{".tfvars", "Terraform"},
		{".v", ""},
		{".h", ""},
	}
	for _, tc := range cases {
		t.Run(tc.extension, func(t *testing.T) {
			got, ok := extendedLanguage(tc.extension)
			if got != tc.language || ok != (tc.language != "") {
				t.Fatalf("extendedLanguage(%q) = %q, %v; want %q", tc.extension, got, ok, tc.language)
			}
		})
	}
}
