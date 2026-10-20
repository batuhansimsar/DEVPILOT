package main

import (
	"bytes"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestDoctorJSON(t *testing.T) {
	root := t.TempDir()
	if err := os.WriteFile(filepath.Join(root, "go.mod"), []byte("module example.com/demo\n"), 0600); err != nil {
		t.Fatal(err)
	}
	var out, errors bytes.Buffer
	if code := run([]string{"doctor", "--json", root}, &out, &errors); code != 0 {
		t.Fatalf("exit=%d stderr=%s", code, errors.String())
	}
	if !strings.Contains(out.String(), `"languages"`) || !strings.Contains(out.String(), `"Go"`) {
		t.Fatalf("unexpected JSON: %s", out.String())
	}
}
func TestRefuseUntrustedTests(t *testing.T) {
	var out, errors bytes.Buffer
	if code := run([]string{"test", t.TempDir()}, &out, &errors); code != 2 || !strings.Contains(errors.String(), "--trust") {
		t.Fatalf("code=%d stderr=%s", code, errors.String())
	}
}
func TestInvalidArgs(t *testing.T) {
	var out, errors bytes.Buffer
	if code := run([]string{"doctor", "one", "two"}, &out, &errors); code != 2 {
		t.Fatalf("exit=%d", code)
	}
}
