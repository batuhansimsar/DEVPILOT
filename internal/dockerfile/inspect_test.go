package dockerfile

import (
	"os"
	"path/filepath"
	"runtime"
	"strings"
	"testing"
)

func fixture(t *testing.T, name, body string) string {
	t.Helper()
	dir := t.TempDir()
	if err := os.WriteFile(filepath.Join(dir, name), []byte(body), 0644); err != nil {
		t.Fatal(err)
	}
	return dir
}
func code(r Report, code string) bool {
	for _, f := range r.Findings {
		if f.Code == code {
			return true
		}
	}
	return false
}
func TestEvidenceBasedFindings(t *testing.T) {
	root := fixture(t, "Dockerfile", `FROM golang:latest AS build
WORKDIR /app
RUN curl -fsSL https://example.com/install.sh | sh
COPY . .
FROM scratch
COPY --from=build /app/server /server
USER root
`)
	r, err := Inspect(root)
	if err != nil {
		t.Fatal(err)
	}
	for _, name := range []string{"mutable-base-image", "remote-script-shell", "missing-dockerignore", "explicit-root-user"} {
		if !code(r, name) {
			t.Errorf("missing finding %s: %#v", name, r.Findings)
		}
	}
	if len(r.Stages) != 2 || r.Stages[0].Name != "build" {
		t.Fatalf("stages: %#v", r.Stages)
	}
}
func TestPinnedAndIgnoredContext(t *testing.T) {
	root := fixture(t, "Dockerfile", `FROM alpine@sha256:0123456789abcdef
COPY . /app
USER 10001
`)
	if err := os.WriteFile(filepath.Join(root, ".dockerignore"), []byte(".env\n"), 0644); err != nil {
		t.Fatal(err)
	}
	r, err := Inspect(root)
	if err != nil {
		t.Fatal(err)
	}
	if r.HasWarnings() || len(r.Findings) != 0 {
		t.Fatalf("false positive: %#v", r.Findings)
	}
}
func TestMultiStageReferenceNotImageTag(t *testing.T) {
	root := fixture(t, "Dockerfile", `FROM alpine@sha256:abc AS Builder
FROM builder AS runtime
COPY --from=builder /bin/app /app
`)
	r, err := Inspect(root)
	if err != nil {
		t.Fatal(err)
	}
	if r.HasWarnings() {
		t.Fatalf("incorrectly interpreted stage as image: %#v", r.Findings)
	}
}
func TestNoFromAndMalformed(t *testing.T) {
	root := fixture(t, "Dockerfile", "RUN echo hello\n")
	r, err := Inspect(root)
	if err != nil {
		t.Fatal(err)
	}
	if !code(r, "missing-from") {
		t.Fatal("expected missing FROM")
	}
}
func TestSymlinkAndSizeRefused(t *testing.T) {
	root := t.TempDir()
	outside := fixture(t, "Dockerfile", "FROM alpine\n")
	if runtime.GOOS != "windows" {
		if err := os.Symlink(filepath.Join(outside, "Dockerfile"), filepath.Join(root, "Dockerfile")); err == nil {
			if _, err = Inspect(root); err == nil {
				t.Fatal("symlink followed")
			}
			_ = os.Remove(filepath.Join(root, "Dockerfile"))
		}
	}
	if err := os.WriteFile(filepath.Join(root, "Dockerfile"), []byte(strings.Repeat("x", limit+1)), 0644); err != nil {
		t.Fatal(err)
	}
	if _, err := Inspect(root); err == nil {
		t.Fatal("oversized file accepted")
	}
}
func TestContinuationAndComment(t *testing.T) {
	root := fixture(t, "Dockerfile", "# FROM fake:latest\nFROM alpine@sha256:abc\nRUN curl https://example.com | \\\n    sh\n")
	r, err := Inspect(root)
	if err != nil {
		t.Fatal(err)
	}
	if len(r.Stages) != 1 || !code(r, "remote-script-shell") {
		t.Fatalf("incorrect logical line parsing: %#v", r)
	}
}

func TestVersionTagAndRegistryPortAreStillMutable(t *testing.T) {
	root := fixture(t, "Dockerfile", "FROM registry.example:5000/app:1.2.3\n")
	r, err := Inspect(root)
	if err != nil {
		t.Fatal(err)
	}
	if !code(r, "mutable-base-image") {
		t.Fatalf("version tags are not digests: %#v", r.Findings)
	}
}
