package main

import (
	"bytes"
	"context"
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestDoctorSARIFCLI(t *testing.T) {
	root := t.TempDir()
	if err := os.WriteFile(filepath.Join(root, "go.mod"), []byte("module example.com/x\n\ngo 1.23\n"), 0600); err != nil {
		t.Fatal(err)
	}
	var out, errOut bytes.Buffer
	code := run(context.Background(), []string{"doctor", "--sarif", root}, &out, &errOut)
	if code != 0 {
		t.Fatalf("doctor status=%d stderr=%s", code, errOut.String())
	}
	var doc struct {
		Version string `json:"version"`
		Runs []struct { Tool struct { Driver struct { Name string `json:"name"` } `json:"driver"` } `json:"tool"` } `json:"runs"`
	}
	if err := json.Unmarshal(out.Bytes(), &doc); err != nil || doc.Version != "2.1.0" || len(doc.Runs) != 1 || doc.Runs[0].Tool.Driver.Name != "DevPilot" {
		t.Fatalf("invalid SARIF output: %v, %s", err, out.String())
	}
	out.Reset()
	errOut.Reset()
	if code := run(context.Background(), []string{"doctor", "--sarif", "--json", root}, &out, &errOut); code != 2 || !strings.Contains(errOut.String(), "mutually exclusive") {
		t.Fatalf("invalid conflict handling: status=%d error=%s", code, errOut.String())
	}
}
