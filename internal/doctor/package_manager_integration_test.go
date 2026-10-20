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

func TestInvalidNodeManagerCannotSelectRunner(t *testing.T) {
	cases := []struct {
		name, spec string
		lockfile   bool
	}{
		{"dist tag", "pnpm@latest", false},
		{"version range", "yarn@^4.0.0", false},
		{"extra at-sign", "bun@1.1.0@other", false},
		{"invalid with npm lockfile", "pnpm@latest", true},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			dir := t.TempDir()
			write(t, dir, "package.json", `{"packageManager":"`+tc.spec+`","scripts":{"test":"echo ok"}}`)
			if tc.lockfile {
				write(t, dir, "package-lock.json", "{}")
			}
			r, err := Inspect(dir)
			if err != nil {
				t.Fatal(err)
			}
			if r.PackageManager != "npm" || r.Tests == nil || r.Tests.Executable != "npm" {
				t.Fatalf("invalid declaration selected executable: %+v", r)
			}
			if !finding(r, "package-manager-invalid") {
				t.Fatalf("expected invalid packageManager warning, got %+v", r.Findings)
			}
			if finding(r, "js-package-manager-mismatch") {
				t.Fatalf("invalid declaration must not emit a lockfile mismatch: %+v", r.Findings)
			}
		})
	}
}
