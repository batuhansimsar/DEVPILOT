package analyze

import "testing"

func TestExtendedLanguage(t *testing.T) {
	cases := []struct {
		extension string
		want      string
	}{
		{".hh", "C++"}, {".hpp", "C++"}, {".hxx", "C++"},
		{".cxx", "C++"}, {".c++", "C++"}, {".ixx", "C++"},
		{".cppm", "C++"}, {".kts", "Kotlin"}, {".csx", "C#"},
		{".mm", "Objective-C++"},
		{".tfvars", "Terraform"}, {".proto", "Protocol Buffers"},
		{".graphql", "GraphQL"}, {".gql", "GraphQL"},
		{".prisma", "Prisma"}, {".nix", "Nix"}, {".cue", "CUE"},
		{".pyi", "Python"}, {".pyw", "Python"},
		{".pyx", "Cython"}, {".pxd", "Cython"}, {".pxi", "Cython"},
	}
	for _, tc := range cases {
		t.Run(tc.extension, func(t *testing.T) {
			if got, ok := extendedLanguage(tc.extension); !ok || got != tc.want {
				t.Fatalf("extendedLanguage(%q) = (%q, %v), want (%q, true)", tc.extension, got, ok, tc.want)
			}
		})
	}
	for _, extension := range []string{".h", ".m", ".txt", ".hpp.bak", ".pyi.bak", "", ".HPP"} {
		if got, ok := extendedLanguage(extension); ok || got != "" {
			t.Errorf("extendedLanguage(%q) = (%q, %v), want no match", extension, got, ok)
		}
	}
}
