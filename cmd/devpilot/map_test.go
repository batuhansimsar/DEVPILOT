package main

import (
	"bytes"
	"encoding/json"
	"os"
	"path/filepath"
	"testing"

	"github.com/batuhansimsar/DEVPILOT/internal/workspace"
)

func TestMapCommandJSON(t *testing.T) {
	dir := t.TempDir()
	if err := os.MkdirAll(filepath.Join(dir, "services", "api"), 0755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(dir, "services", "api", "go.mod"), []byte("module example.com/api"), 0600); err != nil {
		t.Fatal(err)
	}
	var stdout, stderr bytes.Buffer
	if code := runMap([]string{"--json", dir}, &stdout, &stderr); code != 0 {
		t.Fatalf("exit %d: %s", code, stderr.String())
	}
	var data workspace.Map
	if err := json.Unmarshal(stdout.Bytes(), &data); err != nil {
		t.Fatal(err)
	}
	if len(data.Projects) != 1 || data.Projects[0].Path != "services/api" {
		t.Fatalf("unexpected projects: %+v", data.Projects)
	}
}

func TestMapCommandInvalidArguments(t *testing.T) {
	for _, args := range [][]string{{"--unknown"}, {"a", "b"}, {"/a/path/that/does/not/exist"}} {
		var stdout, stderr bytes.Buffer
		if code := runMap(args, &stdout, &stderr); code != 2 || stderr.Len() == 0 {
			t.Fatalf("args %v returned %d stderr %q", args, code, stderr.String())
		}
	}
}
