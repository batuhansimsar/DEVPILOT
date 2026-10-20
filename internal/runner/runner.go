// Package runner executes only explicitly trusted, detected test commands.
package runner

import (
	"context"
	"errors"
	"fmt"
	"io"
	"os/exec"
	"time"

	"github.com/batuhansimsar/DEVPILOT/internal/doctor"
)

var ErrUntrusted = errors.New("execution requires --trust: project test scripts may run arbitrary code")
var ErrNoTests = errors.New("no supported test command detected")

// Run never launches a shell. A trust decision must be made by the caller.
// Stdout and stderr are streamed without collecting potentially sensitive logs.
func Run(ctx context.Context, r doctor.Report, trusted bool, out, errOut io.Writer, timeout time.Duration) error {
	if !trusted {
		return ErrUntrusted
	}
	if len(r.TestCommands) == 0 {
		return ErrNoTests
	}
	if timeout <= 0 {
		return errors.New("timeout must be positive")
	}
	t := r.TestCommands[0]
	if _, err := exec.LookPath(t.Tool); err != nil {
		return fmt.Errorf("required test runner %q unavailable: %w", t.Tool, err)
	}
	ctx, cancel := context.WithTimeout(ctx, timeout)
	defer cancel()
	cmd := exec.CommandContext(ctx, t.Tool, t.Args...)
	cmd.Dir = r.Root
	cmd.Stdout = out
	cmd.Stderr = errOut
	cmd.Stdin = nil
	// Do not inherit any process-level shell: args are fixed by the detector.
	if err := cmd.Run(); err != nil {
		if errors.Is(ctx.Err(), context.DeadlineExceeded) {
			return fmt.Errorf("test timeout after %s: %w", timeout, ctx.Err())
		}
		return fmt.Errorf("test command failed: %w", err)
	}
	return nil
}
