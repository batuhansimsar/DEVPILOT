package doctor

import "testing"

func TestHasPytestTOMLTable(t *testing.T) {
	for _, tc := range []struct {
		name, content string
		want          bool
	}{
		{"real ini options", "[tool.pytest.ini_options]\naddopts = [\"-q\"]", true},
		{"real native pytest", "[tool.pytest]\naddopts = [\"-q\"]", true},
		{"BOM and comment", "\ufeff [tool.pytest] # enabled\r\n", true},
		{"commented table", "# [tool.pytest]\n", false},
		{"suffix table", "[tool.pytest.extra]\n", false},
		{"invalid trailing content", "[tool.pytest] trailing\n", false},
		{"literal multiline payload", "[project]\ndescription = '''\n[tool.pytest]\n'''\n", false},
		{"basic multiline payload", "[project]\ndescription = \"\"\"\n[tool.pytest.ini_options]\n\"\"\"\n", false},
		{"comment with triple delimiters", "# '''\n[tool.pytest]\n", true},
		{"single quoted triple text", "note = \"not a ''' multiline value\"\n[tool.pytest]\n", true},
		{"closing literal and next table", "description = '''\n[tool.pytest]\n'''\n[tool.pytest.ini_options]\n", true},
		{"closing basic on same line", "description = \"\"\"a\"\"\"\n[tool.pytest]\n", true},
		{"escaped basic delimiter", "description = \"\"\"some \\\"\"\"\n[tool.pytest]\n\"\"\"\n", false},
	} {
		t.Run(tc.name, func(t *testing.T) {
			if got := hasPytestTOMLTable([]byte(tc.content)); got != tc.want {
				t.Fatalf("hasPytestTOMLTable()=%t, want %t for %q", got, tc.want, tc.content)
			}
		})
	}
}
