// Package share produces portable, reviewable diagnostics without exposing
// full local paths, Git branches or environment variable names by default.
package share

import (
	"fmt"
	"io"
	"path/filepath"
	"strings"
)

type Finding struct {
	Level   string
	Code    string
	Message string
	Remedy  string
}
type Snapshot struct {
	Workspace      string
	Languages      []string
	Frameworks     []string
	PackageManager string
	TestCommand    string
	Findings       []Finding
}

// Markdown writes a best-effort redacted snapshot. Always review the output
// before posting it publicly: project-specific finding text may be sensitive.
func Markdown(w io.Writer, s Snapshot) error {
	clean := func(v string) string {
		if s.Workspace != "" {
			for _, path := range []string{s.Workspace, filepath.ToSlash(s.Workspace), filepath.FromSlash(s.Workspace)} {
				if path != "" {
					v = strings.ReplaceAll(v, path, "[workspace]")
				}
			}
		}
		v = strings.Map(func(r rune) rune {
			if r == '\r' || r == '\n' || r == '\t' || r < 32 || r == 127 {
				return ' '
			}
			return r
		}, v)
		v = strings.ReplaceAll(v, "|", "\\|")
		return v
	}
	label := func(values []string) string {
		if len(values) == 0 {
			return "Not detected"
		}
		return clean(strings.Join(values, ", "))
	}
	var b strings.Builder
	fmt.Fprintln(&b, "# DevPilot diagnostic snapshot")
	fmt.Fprintln(&b)
	fmt.Fprintln(&b, "> Generated locally. Full workspace paths, Git branches, and environment key names are intentionally excluded. **Review before sharing.**")
	fmt.Fprintln(&b)
	fmt.Fprintln(&b, "## Detected stack")
	fmt.Fprintf(&b, "- Languages: %s\n", label(s.Languages))
	fmt.Fprintf(&b, "- Frameworks: %s\n", label(s.Frameworks))
	pm := s.PackageManager
	if pm == "" {
		pm = "Not detected"
	}
	fmt.Fprintf(&b, "- Package manager: %s\n", clean(pm))
	if s.TestCommand != "" {
		fmt.Fprintf(&b, "- Discovered test: %s (not executed)\n", clean(s.TestCommand))
	}
	fmt.Fprintln(&b)
	fmt.Fprintln(&b, "## Findings")
	fmt.Fprintln(&b)
	fmt.Fprintln(&b, "| Level | Check | Evidence-based observation | Suggested next step |")
	fmt.Fprintln(&b, "| --- | --- | --- | --- |")
	n := 0
	for _, f := range s.Findings {
		// Environment variable names and Git branch names are unnecessary
		// for collaborative issue triage.
		if strings.HasPrefix(f.Code, "git-") {
			continue
		}
		message, remedy := f.Message, f.Remedy
		if strings.HasPrefix(f.Code, "env-") {
			message = "Environment configuration observation (variable names and values redacted)."
			remedy = "Review environment configuration privately."
		}
		fmt.Fprintf(&b, "| %s | %s | %s | %s |\n", clean(f.Level), clean(f.Code), clean(message), clean(remedy))
		n++
	}
	if n == 0 {
		fmt.Fprintln(&b, "| info | no-findings | No shareable findings. | — |")
	}
	fmt.Fprintln(&b)
	fmt.Fprintln(&b, "_This snapshot is not a security audit. Checks may be incomplete._")
	_, err := io.WriteString(w, b.String())
	return err
}
