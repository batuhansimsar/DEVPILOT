package runner

import (
	"os"
	"strings"
	"testing"
	"time"

	"github.com/batuhansimsar/DEVPILOT/internal/doctor"
)

func TestTrustIsMandatory(t *testing.T) {
	_, err := Run(t.TempDir(), doctor.TestCommand{Program: "go", Args: []string{"version"}, Directory: "."}, false, time.Second)
	if err == nil || !strings.Contains(err.Error(), "--trust") {
		t.Fatalf("trust must be required, got: %v", err)
	}
}
func TestRunAndRedact(t *testing.T) {
	cmd := doctor.TestCommand{Program: os.Args[0], Args: []string{"-test.run=TestChildCommand", "--", "redact"}, Directory: "."}
	r, err := Run(t.TempDir(), cmd, true, 10*time.Second)
	if err != nil {
		t.Fatal(err)
	}
	if !strings.Contains(r.Output, "token=[REDACTED]") || strings.Contains(r.Output, "sensitive-value") {
		t.Fatalf("not redacted: %q", r.Output)
	}
}
func TestRunTimeout(t *testing.T) {
	cmd := doctor.TestCommand{Program: os.Args[0], Args: []string{"-test.run=TestChildCommand", "--", "sleep"}, Directory: "."}
	_, err := Run(t.TempDir(), cmd, true, 15*time.Millisecond)
	if err == nil || !strings.Contains(err.Error(), "timed out") {
		t.Fatalf("expected timeout: %v", err)
	}
}
func TestChildCommand(t *testing.T) {
	for i, v := range os.Args {
		if v == "--" && i+1 < len(os.Args) {
			switch os.Args[i+1] {
			case "redact":
				println("token=sensitive-value")
				return
			case "sleep":
				time.Sleep(time.Second)
				return
			}
		}
	}
}
