package doctor

import (
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func fixture(t *testing.T, files map[string]string) string {
	t.Helper()
	dir := t.TempDir()
	for n, c := range files {
		if err := os.WriteFile(filepath.Join(dir, n), []byte(c), 0600); err != nil {
			t.Fatal(err)
		}
	}
	return dir
}
func TestPythonHasPytest(t *testing.T) {
	cases := []struct {
		name  string
		files map[string]string
		want  bool
	}{
		{"plain pyproject", map[string]string{"pyproject.toml": "[project]\nname='hello'\n"}, false},
		{"config section", map[string]string{"pyproject.toml": "[tool.pytest.ini_options]\ntestpaths=['tests']\n"}, true},
		{"pytest in requirements", map[string]string{"requirements.txt": "# pytest==5\nflask>=3\npytest>=8\n"}, true},
		{"cov plugin not pytest", map[string]string{"requirements.txt": "pytest-cov>=5\n"}, false},
		{"comment only", map[string]string{"pyproject.toml": "[project]\n# dependencies=['pytest>=8']\n"}, false},
		{"poetry dependency", map[string]string{"pyproject.toml": "[tool.poetry.group.test.dependencies]\npytest = '^8'\n"}, true},
		{"PEP621 optional", map[string]string{"pyproject.toml": "[project.optional-dependencies]\ntest=['pytest>=8']\n"}, true},
		{"unrelated pyproject description", map[string]string{"pyproject.toml": "[project]\ndescription='using pytest quickly'\n"}, false},
		{"requirements commented", map[string]string{"requirements.txt": "# pytest==7\nblack>=24\n"}, false},
		{"config ini", map[string]string{"pytest.ini": "[pytest]\n"}, true},
		{"setup cfg", map[string]string{"setup.cfg": "[tool:pytest]\naddopts=-q\n"}, true},
		{"conftest", map[string]string{"conftest.py": "# pytest fixture\n"}, true},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			got := pythonHasPytest(fixture(t, tc.files))
			if got != tc.want {
				t.Fatalf("got=%v want=%v", got, tc.want)
			}
		})
	}
}
func TestPythonHasPytestDoesNotFollowSymlink(t *testing.T) {
	dir := t.TempDir()
	outside := fixture(t, map[string]string{"requirements.txt": "pytest>=8"})
	if err := os.Symlink(filepath.Join(outside, "requirements.txt"), filepath.Join(dir, "requirements.txt")); err != nil {
		t.Skipf("symlinks unavailable: %v", err)
	}
	if pythonHasPytest(dir) {
		t.Fatal("symlink was followed")
	}
}
func TestPythonHasPytestRejectsOversize(t *testing.T) {
	dir := fixture(t, map[string]string{"requirements.txt": strings.Repeat("pytest>=8\n", 200000)})
	if pythonHasPytest(dir) {
		t.Fatal("oversized file was inspected")
	}
}
