package doctor

import (
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"testing"
)

func TestRequiredGoVersion(t *testing.T) {
	cases := []struct {
		input, want string
		valid       bool
	}{
		{"module example.net/project\ngo 1.23\n", "1.23", true},
		{"// go 8.0\n\tgo 1.22.4 // reason\n", "1.22.4", true},
		{"module x\n go 1.24rc1\n", "", false},
		{"module x\n", "", false},
	}
	for _, tc := range cases {
		got, ok := requiredGoVersion([]byte(tc.input))
		if ok != tc.valid || (ok && got.String() != tc.want) {
			t.Errorf("%q => %s, %v", tc.input, got, ok)
		}
	}
}
func TestRunningGoVersion(t *testing.T) {
	for _, tc := range []struct {
		input, want string
		valid       bool
	}{
		{"go version go1.23.2 linux/amd64", "1.23.2", true},
		{"go version go1.24 windows/amd64", "1.24", true},
		{"go version devel go1.25-abc linux/amd64", "", false},
	} {
		got, ok := runningGoVersion(tc.input)
		if ok != tc.valid || (ok && got.String() != tc.want) {
			t.Errorf("%q => %s, %v", tc.input, got, ok)
		}
	}
}
func TestVersionOrdering(t *testing.T) {
	old, _ := parseGoVersion("1.23.1")
	required, _ := parseGoVersion("1.23.2")
	if !old.lessThan(required) || required.lessThan(old) || old.lessThan(old) {
		t.Fatal("incorrect version ordering")
	}
	if _, ok := parseGoVersion("1.23-beta"); ok {
		t.Fatal("accepted prerelease as stable")
	}
}
func TestOlderToolchainProducesEvidenceBasedWarning(t *testing.T) {
	if _, err := exec.LookPath("go"); err != nil {
		t.Skip("Go not installed")
	}
	root := t.TempDir()
	if err := os.WriteFile(filepath.Join(root, "go.mod"), []byte("module example.com/repo\ngo 99.1\n"), 0600); err != nil {
		t.Fatal(err)
	}
	found := false
	inspectGoVersion(root, func(level, code, message, remedy string) {
		if code == "go-version-too-old" {
			found = true
			if level != "warning" || !strings.Contains(message, "99.1") || remedy == "" {
				t.Errorf("bad finding: %s %s %s", level, message, remedy)
			}
		}
	})
	if !found {
		t.Fatal("expected minimum-version warning")
	}
}
