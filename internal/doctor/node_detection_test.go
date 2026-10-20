package doctor

import (
	"encoding/json"
	"strings"
	"testing"
)

func TestConflictingNodeLockfiles(t *testing.T) {
	dir := t.TempDir()
	write(t, dir, "package.json", `{"scripts":{"test":"vitest run"}}`)
	write(t, dir, "yarn.lock", "# yarn")
	write(t, dir, "package-lock.json", "{}")
	r, err := Inspect(dir)
	if err != nil {
		t.Fatal(err)
	}
	if !finding(r, "node-lockfile-conflict") {
		t.Fatalf("expected conflicting lockfiles warning: %+v", r.Findings)
	}
	if r.PackageManager != "yarn" {
		t.Fatalf("expected deterministic manager, got %q", r.PackageManager)
	}
	foundEvidence := false
	for _, f := range r.Findings {
		if f.Code == "node-lockfile-conflict" {
			foundEvidence = strings.Contains(f.Message, "npm") && strings.Contains(f.Message, "yarn")
		}
	}
	if !foundEvidence {
		t.Fatal("warning did not identify conflicting managers")
	}
}

func TestSameManagerDualBunLocksNotConflict(t *testing.T) {
	dir := t.TempDir()
	write(t, dir, "package.json", "{}")
	write(t, dir, "bun.lock", "")
	write(t, dir, "bun.lockb", "")
	r, err := Inspect(dir)
	if err != nil {
		t.Fatal(err)
	}
	if finding(r, "node-lockfile-conflict") {
		t.Fatalf("same package manager is not a cross-manager conflict: %+v", r.Findings)
	}
}

func TestPlaceholderAndEmptyNodeScriptsAreNotTests(t *testing.T) {
	for _, script := range []string{"", "echo \"Error: no test specified\" && exit 1", "ECHO no TEST specified"} {
		t.Run(script, func(t *testing.T) {
			dir := t.TempDir()
			data := map[string]any{"scripts": map[string]string{"test": script}}
			// JSON strings are encoded by a typed fixture to avoid invalid escaping.
			body, err := json.Marshal(data)
			if err != nil {
				t.Fatal(err)
			}
			write(t, dir, "package.json", string(body))
			r, err := Inspect(dir)
			if err != nil {
				t.Fatal(err)
			}
			if r.Tests != nil || !finding(r, "no-test-command") {
				t.Fatalf("placeholder should not register a test command: %+v", r)
			}
		})
	}
}

func TestRealNodeTestCommandStillDiscovered(t *testing.T) {
	dir := t.TempDir()
	write(t, dir, "package.json", `{"scripts":{"test":"vitest run"}}`)
	r, err := Inspect(dir)
	if err != nil {
		t.Fatal(err)
	}
	if r.Tests == nil || r.Tests.Executable != "npm" {
		t.Fatalf("expected npm test discovery: %+v", r.Tests)
	}
}
