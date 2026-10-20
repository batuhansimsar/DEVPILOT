package doctor

import (
	"strings"
	"testing"
)

func TestNodeDeclaredManagerWithoutLockfile(t *testing.T) {
	dir := t.TempDir()
	write(t, dir, "package.json", `{"packageManager":"pnpm@9.3.0","scripts":{"test":"vitest run"}}`)
	r, err := Inspect(dir)
	if err != nil {
		t.Fatal(err)
	}
	if r.PackageManager != "pnpm" || r.Tests == nil || r.Tests.Executable != "pnpm" {
		t.Fatalf("expected pnpm runner from packageManager declaration, got %+v", r)
	}
}

func TestNodeDeclaredManagerMismatch(t *testing.T) {
	dir := t.TempDir()
	write(t, dir, "package.json", `{"packageManager":"yarn@4.0.0","scripts":{"test":"jest"}}`)
	write(t, dir, "pnpm-lock.yaml", "lockfileVersion: '9.0'")
	r, err := Inspect(dir)
	if err != nil {
		t.Fatal(err)
	}
	if r.PackageManager != "pnpm" || !finding(r, "js-package-manager-mismatch") || !r.HasWarnings() {
		t.Fatalf("expected mismatch warning with authoritative pnpm lockfile, got %+v", r)
	}
	for _, f := range r.Findings {
		if f.Code == "js-package-manager-mismatch" && (!strings.Contains(f.Message, "yarn") || !strings.Contains(f.Message, "pnpm")) {
			t.Fatalf("mismatch must show both managers: %s", f.Message)
		}
	}
}
