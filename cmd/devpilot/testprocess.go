package main

import (
	"context"
	"os"
	"os/exec"
	"strings"
	"time"
)

// newTrustedTestCommand provides bounded process waiting and limits inadvertent
// credential inheritance. Project scripts remain arbitrary code, so the
// caller must enforce the explicit --trust boundary before calling this.
func newTrustedTestCommand(ctx context.Context, dir, executable string, args ...string) *exec.Cmd {
	cmd := exec.CommandContext(ctx, executable, args...)
	cmd.Dir = dir
	cmd.Env = filteredTestEnvironment(os.Environ())
	// CommandContext kills only the direct process. Descendants may keep its
	// stdout/stderr pipe handles open; never wait indefinitely for pipe EOF.
	cmd.WaitDelay = 2 * time.Second
	return cmd
}

// filteredTestEnvironment is defense-in-depth, NOT sandbox isolation. Tests can
// still read files, use the network, or load secrets with uncommon variable names.
func filteredTestEnvironment(entries []string) []string {
	result := make([]string, 0, len(entries))
	for _, entry := range entries {
		key, _, ok := strings.Cut(entry, "=")
		if !ok {
			continue
		}
		upper := strings.ToUpper(key)
		omit := false
		for _, marker := range []string{"TOKEN", "SECRET", "PASSWORD", "PASSWD", "PRIVATE_KEY", "API_KEY", "CREDENTIAL", "AUTHORIZATION"} {
			if strings.Contains(upper, marker) {
				omit = true
				break
			}
		}
		if !omit {
			result = append(result, entry)
		}
	}
	return result
}
