package runner

import (
	"bytes"
	"context"
	"errors"
	"github.com/batuhansimsar/DEVPILOT/internal/doctor"
	"testing"
	"time"
)

func TestRequiresTrust(t *testing.T) {
	r := doctor.Report{Root: t.TempDir(), TestCommands: []doctor.TestCommand{{Tool: "go", Args: []string{"version"}}}}
	err := Run(context.Background(), r, false, &bytes.Buffer{}, &bytes.Buffer{}, time.Second)
	if !errors.Is(err, ErrUntrusted) {
		t.Fatalf("expected trust guard, got %v", err)
	}
}
func TestNoTests(t *testing.T) {
	err := Run(context.Background(), doctor.Report{Root: t.TempDir()}, true, &bytes.Buffer{}, &bytes.Buffer{}, time.Second)
	if !errors.Is(err, ErrNoTests) {
		t.Fatalf("expected no tests, got %v", err)
	}
}
func TestExecutesSafeFixture(t *testing.T) {
	r := doctor.Report{Root: t.TempDir(), TestCommands: []doctor.TestCommand{{Tool: "go", Args: []string{"version"}}}}
	var out bytes.Buffer
	if err := Run(context.Background(), r, true, &out, &bytes.Buffer{}, 10*time.Second); err != nil {
		t.Fatal(err)
	}
	if out.Len() == 0 {
		t.Fatal("expected command output")
	}
}
