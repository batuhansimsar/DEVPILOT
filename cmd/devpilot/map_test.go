package main

import (
	"bytes"
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
	"testing"

	"github.com/batuhansimsar/DEVPILOT/internal/projecttree"
)

func TestMapJSONFromCLI(t *testing.T) {
	root := t.TempDir()
	if err := os.WriteFile(filepath.Join(root, "README.md"), []byte("hello"), 0600); err != nil {
		t.Fatal(err)
	}
	var out, errs bytes.Buffer
	if exit := runMap([]string{"--json", root}, &out, &errs); exit != 0 {
		t.Fatalf("exit=%d stderr=%s", exit, errs.String())
	}
	var m projecttree.Map
	if err := json.Unmarshal(out.Bytes(), &m); err != nil {
		t.Fatal(err)
	}
	if len(m.Entries) != 1 || m.Entries[0].Path != "README.md" {
		t.Fatalf("entries=%+v", m.Entries)
	}
}

func TestMapCLIRejectsBadDepth(t *testing.T) {
	var out, errs bytes.Buffer
	if exit := runMap([]string{"--depth=0"}, &out, &errs); exit != 2 || !strings.Contains(errs.String(), "depth") {
		t.Fatalf("exit=%d stderr=%s", exit, errs.String())
	}
}
