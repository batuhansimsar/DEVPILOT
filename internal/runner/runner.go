// Package runner explicitly executes selected, discovered test commands.
package runner

import (
	"bytes"
	"context"
	"errors"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"regexp"
	"strings"
	"sync"
	"time"

	"github.com/batuhansimsar/DEVPILOT/internal/doctor"
)

type Result struct {
	Command   doctor.TestCommand
	Output    string
	Duration  time.Duration
	ExitCode  int
	Truncated bool
}

// boundedBuffer never retains more than limit bytes, even if a test floods stdout.
type boundedBuffer struct {
	mu        sync.Mutex
	b         bytes.Buffer
	truncated bool
	limit     int
}

func (w *boundedBuffer) Write(p []byte) (int, error) {
	w.mu.Lock()
	defer w.mu.Unlock()
	space := w.limit - w.b.Len()
	if len(p) > space {
		w.truncated = true
	}
	if space > 0 {
		w.b.Write(p[:min(len(p), space)])
	}
	return len(p), nil
}
func (w *boundedBuffer) String() string { w.mu.Lock(); defer w.mu.Unlock(); return w.b.String() }

var mask = regexp.MustCompile(`(?im)\b(token|api[_-]?key|password|secret|authorization)\s*[:=]\s*[^\s]+`)

func Run(root string, cmd doctor.TestCommand, trust bool, timeout time.Duration) (Result, error) {
	if !trust {
		return Result{}, errors.New("test execution is disabled until --trust is supplied")
	}
	if timeout <= 0 || timeout > 30*time.Minute {
		return Result{}, errors.New("timeout must be between 1ns and 30m")
	}
	absRoot, err := filepath.Abs(root)
	if err != nil {
		return Result{}, err
	}
	absDir := filepath.Join(absRoot, filepath.FromSlash(cmd.Directory))
	rel, err := filepath.Rel(absRoot, absDir)
	if err != nil || rel == ".." || strings.HasPrefix(rel, ".."+string(filepath.Separator)) {
		return Result{}, errors.New("test directory is outside workspace")
	}
	// Re-check all parent directories, to avoid following a swapped symlink.
	current := absRoot
	if rel != "." {
		for _, p := range strings.Split(rel, string(filepath.Separator)) {
			current = filepath.Join(current, p)
			i, e := os.Lstat(current)
			if e != nil {
				return Result{}, e
			}
			if i.Mode()&os.ModeSymlink != 0 {
				return Result{}, errors.New("test directory contains a symlink")
			}
		}
	}
	if cmd.Program == "" || len(cmd.Args) == 0 {
		return Result{}, errors.New("invalid test command")
	}
	ctx, cancel := context.WithTimeout(context.Background(), timeout)
	defer cancel()
	proc := exec.CommandContext(ctx, cmd.Program, cmd.Args...)
	proc.Dir = absDir
	proc.Env = os.Environ()
	out := &boundedBuffer{limit: 512 * 1024}
	proc.Stdout = out
	proc.Stderr = out
	started := time.Now()
	err = proc.Run()
	result := Result{Command: cmd, Output: mask.ReplaceAllString(out.String(), "$1=[REDACTED]"), Duration: time.Since(started), Truncated: out.truncated, ExitCode: 0}
	if err != nil {
		if ctx.Err() != nil {
			return result, fmt.Errorf("test command timed out or was cancelled: %w", ctx.Err())
		}
		var exit *exec.ExitError
		if errors.As(err, &exit) {
			result.ExitCode = exit.ExitCode()
			return result, fmt.Errorf("test exited with code %d", result.ExitCode)
		}
		return result, fmt.Errorf("cannot execute %s: %w", cmd.Program, err)
	}
	return result, nil
}
