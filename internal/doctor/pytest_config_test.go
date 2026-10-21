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
			if err := os.WriteFile(filepath.Join(root, name), []byte(""), 0600); err != nil {
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
