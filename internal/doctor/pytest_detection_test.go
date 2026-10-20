package doctor

import (
 "os"
 "path/filepath"
 "testing"
)

func TestPyprojectWithoutPytestDoesNotInventTestCommand(t *testing.T) {
 dir := t.TempDir()
 if err := os.WriteFile(filepath.Join(dir, "pyproject.toml"), []byte("[project]\nname = \"example\"\n"), 0600); err != nil { t.Fatal(err) }
 report, err := Inspect(dir)
 if err != nil { t.Fatal(err) }
 if report.Tests != nil { t.Fatalf("pyproject alone does not establish pytest: %+v", report.Tests) }
 if !finding(report, "no-test-command") { t.Fatal("missing no-test-command finding") }
}

func TestPytestTableInPyprojectIsDiscovered(t *testing.T) {
 dir := t.TempDir()
 body := "[project]\nname = \"demo\"\n\n[tool.pytest.ini_options] # valid TOML comment\ntestpaths = [\"tests\"]\n"
 if err := os.WriteFile(filepath.Join(dir, "pyproject.toml"), []byte(body), 0600); err != nil { t.Fatal(err) }
 report, err := Inspect(dir)
 if err != nil { t.Fatal(err) }
 if report.Tests == nil || report.Tests.Executable != "python" { t.Fatalf("expected pytest discovery: %+v", report.Tests) }
 if len(report.Tests.Arguments) != 2 || report.Tests.Arguments[0] != "-m" || report.Tests.Arguments[1] != "pytest" {
  t.Fatalf("unexpected command: %+v", report.Tests)
 }
}

func TestPytestTableCommentAndLookalikesIgnored(t *testing.T) {
 for _, input := range []string{
  "# [tool.pytest.ini_options]\n[project]\nname = \"example\"\n",
  "[tool.pytest.ini_options.extra]\n",
  "[tool.pytest.ini_options]not-a-table\n",
 } {
  if declaresPytest([]byte(input)) { t.Fatalf("false-positive pytest table for %q", input) }
 }
}

func TestExplicitPytestIniIsDetected(t *testing.T) {
 dir := t.TempDir()
 if err := os.WriteFile(filepath.Join(dir, "pytest.ini"), []byte("[pytest]\n"), 0600); err != nil { t.Fatal(err) }
 report, err := Inspect(dir)
 if err != nil { t.Fatal(err) }
 if report.Tests == nil || report.Tests.Executable != "python" { t.Fatalf("expected pytest from pytest.ini: %+v", report.Tests) }
}

func TestConftestFileIsDetected(t *testing.T) {
 dir := t.TempDir()
 if err := os.WriteFile(filepath.Join(dir, "conftest.py"), []byte(""), 0600); err != nil { t.Fatal(err) }
 report, err := Inspect(dir)
 if err != nil { t.Fatal(err) }
 if report.Tests == nil || report.Tests.Executable != "python" { t.Fatalf("expected pytest from conftest.py: %+v", report.Tests) }
}

func TestPytestTableParserAcceptsWhitespace(t *testing.T) {
 if !declaresPytest([]byte("  [tool.pytest.ini_options]  \n")) { t.Fatal("expected valid table") }
}
