package main

import (
	"bytes"
	"encoding/json"
	"github.com/batuhansimsar/DEVPILOT/internal/projecttree"
	"os"
	"path/filepath"
	"testing"
)

func TestCLIJSON(t *testing.T) {
	root := t.TempDir()
	if e := os.WriteFile(filepath.Join(root, "a.go"), []byte("x"), 0600); e != nil {
		t.Fatal(e)
	}
	var out, errOut bytes.Buffer
	code := run([]string{"-json", root}, &out, &errOut)
	if code != 0 {
		t.Fatalf("exit %d: %s", code, errOut.String())
	}
	var r projecttree.Result
	if e := json.Unmarshal(out.Bytes(), &r); e != nil {
		t.Fatal(e)
	}
	if len(r.Entries) != 1 || r.Entries[0].Path != "a.go" {
		t.Fatalf("%+v", r)
	}
}
func TestCLIInvalidDepth(t *testing.T) {
	var out, errOut bytes.Buffer
	if code := run([]string{"-depth", "999"}, &out, &errOut); code != 2 {
		t.Fatalf("exit %d", code)
	}
}
