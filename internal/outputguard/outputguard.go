// Package outputguard bounds trusted test output and masks common credentials.
// The protection is best-effort and is not a security sandbox.
package outputguard

import (
	"fmt"
	"io"
	"os"
	"regexp"
	"sort"
	"strings"
)

const Limit = 256 * 1024

// Buffer caps memory use even if a test emits unbounded output.
type Buffer struct {
	data      []byte
	truncated bool
}

func (b *Buffer) Write(p []byte) (int, error) {
	length := len(p)
	remaining := Limit - len(b.data)
	if remaining > 0 {
		if len(p) > remaining {
			p = p[:remaining]
		}
		b.data = append(b.data, p...)
	}
	if length > remaining {
		b.truncated = true
	}
	return length, nil
}

// Flush writes sanitized output after the process exits, so no raw chunks leak.
// Transformed, encoded and unknown secrets may not be recognized.
func (b *Buffer) Flush(w io.Writer) error {
	if _, err := io.WriteString(w, Redact(string(b.data))); err != nil {
		return err
	}
	if b.truncated {
		_, err := fmt.Fprint(w, "\n[DevPilot: test output truncated at 256 KiB]\n")
		return err
	}
	return nil
}

var assignment = regexp.MustCompile("(?i)(\\b(?:[a-z_][a-z_0-9]*)?(?:token|secret|password|passwd|api_key|private_key|credential)[a-z_0-9]*\\s*[:=]\\s*)[^\\s,;]+")
var githubToken = regexp.MustCompile("(?:gh[pousr]_[A-Za-z0-9_]{20,}|github_pat_[A-Za-z0-9_]{20,})")

// Redact prevents common credential values from appearing in reported test logs.
// It handles known sensitive environment values and token assignments. Neither
// method can identify arbitrary secrets printed by an untrusted script.
func Redact(text string) string {
	values := make([]string, 0)
	for _, entry := range os.Environ() {
		key, value, ok := strings.Cut(entry, "=")
		if !ok || len(value) < 4 {
			continue
		}
		upper := strings.ToUpper(key)
		for _, marker := range []string{"TOKEN", "SECRET", "PASSWORD", "PASSWD", "PRIVATE_KEY", "API_KEY", "CREDENTIAL"} {
			if strings.Contains(upper, marker) {
				values = append(values, value)
				break
			}
		}
	}
	sort.Slice(values, func(i, j int) bool { return len(values[i]) > len(values[j]) })
	for _, value := range values {
		text = strings.ReplaceAll(text, value, "[REDACTED]")
	}
	text = assignment.ReplaceAllString(text, "1[REDACTED]")
	return githubToken.ReplaceAllString(text, "[REDACTED]")
}
