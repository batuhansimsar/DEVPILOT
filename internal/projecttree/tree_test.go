package projecttree

import (
	"bytes"
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func add(t *testing.T, root, path string) {
	t.Helper()
	full := filepath.Join(root, path)
	if err := os.MkdirAll(filepath.Dir(full), 0755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(full, []byte("fake contents"), 0644); err != nil {
		t.Fatal(err)
	}
}
func paths(tree Result) []string {
	out := []string{}
	for _, item := range tree.Entries {
		out = append(out, item.Path)
	}
	return out
}
func TestDepthAndIgnoredDirectories(t *testing.T) {
	root := t.TempDir()
	add(t, root, "cmd/devpilot/main.go")
	add(t, root, ".github/workflows/ci.yml")
	add(t, root, "node_modules/evil/hidden.json")
	add(t, root, ".git/HEAD")
	result, err := Scan(root, 2)
	if err != nil {
		t.Fatal(err)
	}
	list := strings.Join(paths(result), "|")
	if !strings.Contains(list, "cmd/devpilot") || !strings.Contains(list, ".github/workflows") {
		t.Fatalf("missing expected structure: %s", list)
	}
	if strings.Contains(list, "main.go") || strings.Contains(list, "node_modules") || strings.Contains(list, ".git|") || strings.HasPrefix(list, ".git|") {
		t.Fatalf("depth/ignore failure: %s", list)
	}
	result, err = Scan(root, 3)
	if err != nil {
		t.Fatal(err)
	}
	if !strings.Contains(strings.Join(paths(result), "|"), "cmd/devpilot/main.go") {
		t.Fatalf("missing source file: %+v", result)
	}
}
func TestSymlinkNotFollowed(t *testing.T) {
	root := t.TempDir()
	outside := t.TempDir()
	add(t, outside, "secret.txt")
	if err := os.Symlink(outside, filepath.Join(root, "linked")); err != nil {
		t.Skipf("symlinks unsupported: %v", err)
	}
	result, err := Scan(root, 4)
	if err != nil {
		t.Fatal(err)
	}
	if len(result.Entries) != 1 || result.Entries[0].Kind != "symlink" {
		t.Fatalf("unexpected symlink handling: %+v", result)
	}
}
func TestOutputAndJSON(t *testing.T) {
	root := t.TempDir()
	add(t, root, "README.md")
	add(t, root, "src/a.go")
	result, err := Scan(root, 2)
	if err != nil {
		t.Fatal(err)
	}
	var buf bytes.Buffer
	if err := Print(&buf, result); err != nil {
		t.Fatal(err)
	}
	if !strings.Contains(buf.String(), "- src/") || !strings.Contains(buf.String(), "  - a.go") {
		t.Fatalf("unexpected outline: %q", buf.String())
	}
	data, err := json.Marshal(result)
	if err != nil {
		t.Fatal(err)
	}
	var decoded Result
	if err := json.Unmarshal(data, &decoded); err != nil || len(decoded.Entries) != 3 {
		t.Fatalf("invalid JSON: %+v %v", decoded, err)
	}
}
func TestRejectBadPathsAndDepth(t *testing.T) {
	root := t.TempDir()
	add(t, root, "file.txt")
	for _, depth := range []int{0, -1, 7} {
		if _, err := Scan(root, depth); err == nil {
			t.Fatal("accepted invalid depth")
		}
	}
	if _, err := Scan(filepath.Join(root, "file.txt"), 2); err == nil {
		t.Fatal("accepted regular file as directory")
	}
	if _, err := Scan(filepath.Join(root, "missing"), 2); err == nil {
		t.Fatal("accepted missing workspace")
	}
}

func TestTerminalFilenameSanitization(t *testing.T) {
	actual := safeDisplayName("bad\x1b[31m\nname\u202etxt")
	if strings.ContainsAny(actual, "\x1b\n") || strings.ContainsRune(actual, '\u202e') {
		t.Fatalf("unsafe control sequence: %q", actual)
	}
}
