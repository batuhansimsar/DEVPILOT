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
	ctx, cancel := context.WithTimeout(ctx, defaultTimeout)
	defer cancel()
	cmd := exec.CommandContext(ctx, "docker", args...)
	var out bytes.Buffer
	limited := &boundedWriter{remaining: maxOutput, dest: &out}
	cmd.Stdout = limited
	cmd.Stderr = limited
	err := cmd.Run()
	if errors.Is(ctx.Err(), context.DeadlineExceeded) {
		return nil, errors.New("Docker command timed out after 5 seconds")
	}
	if errors.Is(err, errLimit) {
		return nil, fmt.Errorf("Docker output exceeded %d bytes", maxOutput)
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
	if run == nil {
		run = SystemCLI
	}
	out, err := run(ctx, "ps", "--format", "{{json .}}")
	if err != nil {
		return Containers{Items: []json.RawMessage{}, Detail: err.Error()}
	}
	result := Containers{Available: true, Items: []json.RawMessage{}}
	for _, line := range bytes.Split(bytes.TrimSpace(out), []byte("\n")) {
		if len(bytes.TrimSpace(line)) == 0 {
			continue
		}
		if !json.Valid(line) || line[0] != '{' {
			return Containers{Items: []json.RawMessage{}, Detail: "Docker returned invalid container metadata"}
		}
		result.Items = append(result.Items, append(json.RawMessage(nil), line...))
	}
	return result
}
