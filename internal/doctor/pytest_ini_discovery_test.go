package doctor

import (
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestDoctorPytestINIConfigDiscovery(t *testing.T) {
	cases := []struct {
		name, file, content string
		want                bool
	}{
		{"tox pytest", "tox.ini", "[tox]\nenv_list = py\n[pytest]\naddopts = -q\n", true},
		{"setup cfg pytest", "setup.cfg", "[metadata]\nname = app\n[tool:pytest]\n", true},
		{"generic tox", "tox.ini", "[tox]\nenv_list = py\n", false},
		{"generic setup", "setup.cfg", "[metadata]\nname = app\n", false},
		{"wrong tox section", "tox.ini", "[tool:pytest]\n", false},
		{"wrong setup section", "setup.cfg", "[pytest]\n", false},
		{"comment", "tox.ini", "# [pytest]\n", false},
		{"indented continuation", "tox.ini", "[tox]\ndescription =\n [pytest]\n", false},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			root := t.TempDir()
			if err := os.WriteFile(filepath.Join(root, tc.file), []byte(tc.content), 0600); err != nil {
				t.Fatal(err)
			}
			report, err := Inspect(root)
			if err != nil {
				t.Fatal(err)
			}
			if len(report.Languages) != 1 || report.Languages[0] != "Python" {
				t.Fatalf("expected a Python project, got %v", report.Languages)
			}
			if got := report.Tests != nil; got != tc.want {
				t.Fatalf("test runner discovered=%v, want %v; findings=%+v", got, tc.want, report.Findings)
			}
			if tc.want && (report.Tests.Executable != "python" ||
				strings.Join(report.Tests.Arguments, " ") != "-m pytest") {
				t.Fatalf("unexpected test command: %+v", report.Tests)
			}
		})
	}
}

func TestDoctorPytestINIConfigDoesNotFollowSymlinksOrReadHugeFiles(t *testing.T) {
	root := t.TempDir()
	outside := filepath.Join(t.TempDir(), "outside.ini")
	if err := os.WriteFile(outside, []byte("[pytest]\n"), 0600); err != nil {
		t.Fatal(err)
	}
	if err := os.Symlink(outside, filepath.Join(root, "tox.ini")); err != nil {
		t.Skipf("symlink creation unavailable: %v", err)
	}
	if err := os.WriteFile(filepath.Join(root, "setup.cfg"), []byte("[tool:pytest]\n"+strings.Repeat("x", 1024*1024)), 0600); err != nil {
		t.Fatal(err)
	}
	report, err := Inspect(root)
	if err != nil {
		t.Fatal(err)
	}
	if report.Tests != nil {
		t.Fatalf("unsafe INI markers must not select pytest: %+v", report.Tests)
	}
}
