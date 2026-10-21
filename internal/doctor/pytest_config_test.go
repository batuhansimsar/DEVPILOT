package doctor

import (
	"os"
	"path/filepath"
	"testing"
)

func TestDoctorDiscoversPytestConfigOnlyProject(t *testing.T) {
	for _, name := range []string{"pytest.toml", ".pytest.toml", "pytest.ini", ".pytest.ini", "pyproject.toml"} {
		t.Run(name, func(t *testing.T) {
			root := t.TempDir()
			content := ""
			if name == "pyproject.toml" {
				content = "[tool.pytest.ini_options]\n"
			}
			if err := os.WriteFile(filepath.Join(root, name), []byte(content), 0600); err != nil {
				t.Fatal(err)
			}
			report, err := Inspect(root)
			if err != nil {
				t.Fatal(err)
			}
			if len(report.Languages) != 1 || report.Languages[0] != "Python" {
				t.Fatalf("languages: %v", report.Languages)
			}
			if report.Tests == nil || report.Tests.Executable != "python" ||
				len(report.Tests.Arguments) != 2 ||
				report.Tests.Arguments[0] != "-m" || report.Tests.Arguments[1] != "pytest" {
				t.Fatalf("test command for %s: %+v", name, report.Tests)
			}
			if !finding(report, "test-discovered") || finding(report, "unknown-project") {
				t.Fatalf("unexpected findings: %+v", report.Findings)
			}
		})
	}
}

func TestDoctorIgnoresUntrustedPytestConfigMarkers(t *testing.T) {
	root := t.TempDir()
	if err := os.Mkdir(filepath.Join(root, "pytest.toml"), 0700); err != nil {
		t.Fatal(err)
	}
	outside := filepath.Join(t.TempDir(), "outside.toml")
	if err := os.WriteFile(outside, []byte("[pytest]"), 0600); err != nil {
		t.Fatal(err)
	}
	if err := os.Symlink(outside, filepath.Join(root, ".pytest.toml")); err != nil {
		t.Skipf("symlinks unavailable: %v", err)
	}
	report, err := Inspect(root)
	if err != nil {
		t.Fatal(err)
	}
	if len(report.Languages) != 0 || report.Tests != nil {
		t.Fatalf("non-regular pytest configs must be ignored: %+v", report)
	}
}

func TestDoctorPyprojectRequiresPytestConfiguration(t *testing.T) {
	for _, tc := range []struct {
		name    string
		content string
		pytest  bool
	}{
		{"empty", "", false},
		{"project metadata", "[project]\nname = \"my-app\"\n", false},
		{"poetry metadata", "[tool.poetry]\nname = \"my-app\"\n", false},
		{"commented out", "# [tool.pytest.ini_options]\n", false},
		{"other table", "[tool.pytest.ini_options_extra]\n", false},
		{"pytest ini options", "[tool.pytest.ini_options]\ntestpaths = [\"tests\"]\n", true},
		{"pytest 9 table", "[tool.pytest]\naddopts = [\"-q\"]\n", true},
		{"whitespace and comment", " [tool.pytest.ini_options]  # config\r\n", true},
		{"UTF-8 BOM", "\ufeff[tool.pytest.ini_options]\n", true},
	} {
		t.Run(tc.name, func(t *testing.T) {
			root := t.TempDir()
			if err := os.WriteFile(filepath.Join(root, "pyproject.toml"), []byte(tc.content), 0600); err != nil {
				t.Fatal(err)
			}
			report, err := Inspect(root)
			if err != nil {
				t.Fatal(err)
			}
			if len(report.Languages) != 1 || report.Languages[0] != "Python" {
				t.Fatalf("pyproject must identify Python, got %v", report.Languages)
			}
			if (report.Tests != nil) != tc.pytest {
				t.Fatalf("test runner discovered=%v, want %v (findings: %+v)", report.Tests != nil, tc.pytest, report.Findings)
			}
			if finding(report, "test-discovered") != tc.pytest {
				t.Fatalf("unexpected test-discovered finding: %+v", report.Findings)
			}
		})
	}
}

func TestDoctorPyprojectSymlinkNeverInfersPytest(t *testing.T) {
	root := t.TempDir()
	outside := filepath.Join(t.TempDir(), "pyproject.toml")
	if err := os.WriteFile(outside, []byte("[tool.pytest.ini_options]\n"), 0600); err != nil {
		t.Fatal(err)
	}
	if err := os.Symlink(outside, filepath.Join(root, "pyproject.toml")); err != nil {
		t.Skipf("symlinks unavailable: %v", err)
	}
	report, err := Inspect(root)
	if err != nil {
		t.Fatal(err)
	}
	if len(report.Languages) != 0 || report.Tests != nil {
		t.Fatalf("symlinked pyproject must be ignored: %+v", report)
	}
}
