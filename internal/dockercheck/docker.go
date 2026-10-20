// Package dockercheck provides opt-in, read-only Docker diagnostics.
// It never starts, stops, removes or modifies containers.
package dockercheck

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"os/exec"
	"strings"
	"time"
)

const maxOutput = 1024 * 1024
const defaultTimeout = 5 * time.Second

// Daemon is a JSON-friendly summary of local Docker availability.
type Daemon struct {
	Installed bool   `json:"installed"`
	Reachable bool   `json:"reachable"`
	Version   string `json:"server_version,omitempty"`
	Detail    string `json:"detail,omitempty"`
}

// Containers summarizes a read-only docker ps query.
type Containers struct {
	Available bool              `json:"available"`
	Items     []json.RawMessage `json:"containers"`
	Detail    string            `json:"detail,omitempty"`
}

// DockerCLI executes a fixed Docker command without a shell or project hooks.
type DockerCLI func(context.Context, ...string) ([]byte, error)

// SystemCLI invokes docker with a short timeout and limits retained output.
func SystemCLI(ctx context.Context, args ...string) ([]byte, error) {
	if ctx == nil {
		return nil, errors.New("context must not be nil")
	}
	ctx, cancel := context.WithTimeout(ctx, defaultTimeout)
	defer cancel()
	cmd := exec.CommandContext(ctx, "docker", args...)
	// A child process may exit while descendants keep stdout/stderr open.
	// Bound the time Cmd.Wait can spend waiting for inherited pipe EOF.
	cmd.WaitDelay = 250 * time.Millisecond
	var out bytes.Buffer
	limited := &boundedWriter{remaining: maxOutput, dest: &out}
	cmd.Stdout = limited
	cmd.Stderr = limited
	err := cmd.Run()
	if errors.Is(ctx.Err(), context.DeadlineExceeded) {
		return nil, errors.New("Docker command timed out after 5 seconds")
	}
	if errors.Is(err, exec.ErrWaitDelay) {
		return nil, errors.New("Docker output pipe stayed open after command exit")
	}
	if errors.Is(err, errLimit) {
		return nil, fmt.Errorf("Docker output exceeded %d bytes", maxOutput)
	}
	if errors.Is(err, exec.ErrNotFound) {
		return nil, errors.New("Docker CLI not found on PATH")
	}
	if err != nil {
		return nil, fmt.Errorf("Docker command failed: %s", strings.TrimSpace(out.String()))
	}
	return out.Bytes(), nil
}

var errLimit = errors.New("output size limit exceeded")

type boundedWriter struct {
	remaining int
	dest      *bytes.Buffer
}

func (w *boundedWriter) Write(data []byte) (int, error) {
	if len(data) > w.remaining {
		n, _ := w.dest.Write(data[:w.remaining])
		w.remaining = 0
		return n, errLimit
	}
	w.remaining -= len(data)
	return w.dest.Write(data)
}

// Inspect checks whether the Docker CLI and daemon are usable.
func Inspect(ctx context.Context, run DockerCLI) Daemon {
	if ctx == nil {
		return Daemon{Detail: "context must not be nil"}
	}
	if run == nil {
		if _, err := exec.LookPath("docker"); err != nil {
			return Daemon{Detail: "Docker CLI not found on PATH"}
		}
		run = SystemCLI
	}
	out, err := run(ctx, "info", "--format", "{{.ServerVersion}}")
	if err != nil {
		return Daemon{Installed: true, Detail: err.Error()}
	}
	return Daemon{Installed: true, Reachable: true, Version: strings.TrimSpace(string(out))}
}

// List returns metadata for running containers without inspecting secrets.
func List(ctx context.Context, run DockerCLI) Containers {
	if ctx == nil {
		return Containers{Items: []json.RawMessage{}, Detail: "context must not be nil"}
	}
	if run == nil {
		run = SystemCLI
	}
	out, err := run(ctx, "ps", "--format", "{{json .}}")
	if err != nil {
		return Containers{Items: []json.RawMessage{}, Detail: err.Error()}
	}
	result := Containers{Available: true, Items: []json.RawMessage{}}
	for _, line := range bytes.Split(out, []byte("\n")) {
		// JSON permits surrounding whitespace. Normalize each line before
		// validating it, so indented JSONL and CRLF input are accepted.
		line = bytes.TrimSpace(line)
		if len(line) == 0 {
			continue
		}
		if line[0] != '{' || !json.Valid(line) {
			return Containers{Items: []json.RawMessage{}, Detail: "Docker returned invalid container metadata"}
		}
		result.Items = append(result.Items, append(json.RawMessage(nil), line...))
	}
	return result
}
