package analyze

import "testing"

func TestSupplementalModernWebSourceFormats(t *testing.T) {
	for _, tc := range []struct {
		filename, language string
	}{
		{"src/pages/index.astro", "Astro"},
		{"src/components/Nav.ASTRO", "Astro"},
		{"prisma/schema.prisma", "Prisma Schema"},
		{"prisma/DATA.PRISMA", "Prisma Schema"},
		{"docs/guide.mdx", "MDX"},
		{"docs/README.MDX", "MDX"},
	} {
		t.Run(tc.filename, func(t *testing.T) {
			got, ok := supplementalSourceLanguage(tc.filename)
			if !ok || got != tc.language {
				t.Fatalf("supplementalSourceLanguage(%q) = %q, %v; want %q", tc.filename, got, ok, tc.language)
			}
		})
	}
	for _, filename := range []string{"README.md", "schema.prisma.backup", "script.astro.txt"} {
		if got, ok := supplementalSourceLanguage(filename); ok {
			t.Errorf("unrecognized file %q reported as %s", filename, got)
		}
	}
}
