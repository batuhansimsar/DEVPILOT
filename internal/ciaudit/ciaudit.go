// Package ciaudit performs a narrow, offline GitHub Actions reference audit.
// It does not execute workflows or infer safety from action names.
package ciaudit

import (
	"errors"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"regexp"
	"sort"
	"strings"
)

const maxWorkflowBytes = 1 << 20
const maxWorkflows = 100

// Finding is a high-confidence observation about a literal uses: directive.
type Finding struct {
	Code      string `json:"code"`
	Workflow  string `json:"workflow"`
	Line      int    `json:"line"`
	Reference string `json:"reference"`
	Message   string `json:"message"`
	Remedy    string `json:"remedy"`
}
type Report struct {
	Root             string    `json:"root"`
	Workflows        int       `json:"workflows"`
	Actions          int       `json:"actions"`
	ImmutableActions int       `json:"immutable_actions"`
	Findings         []Finding `json:"findings"`
	Skipped          []string  `json:"skipped,omitempty"`
	Truncated        bool      `json:"truncated"`
}

var usesPattern = regexp.MustCompile(`^\s*(?:-\s*)?uses:\s*['"]?([^\s'"#]+)`)
var shaPattern = regexp.MustCompile(`^[a-fA-F0-9]{40}$`)

// Inspect examines only regular .yml/.yaml files immediately under
// .github/workflows. YAML anchors, dynamic uses expressions and reusable
// workflow semantics are deliberately outside this syntax-limited audit.
func Inspect(root string) (Report, error) {
	abs, err := filepath.Abs(root)
	if err != nil {
		return Report{}, err
	}
	st, err := os.Lstat(abs)
	if err != nil {
		return Report{}, fmt.Errorf("workspace: %w", err)
	}
	if !st.IsDir() || st.Mode()&os.ModeSymlink != 0 {
		return Report{}, errors.New("workspace must be a real directory")
	}
	report := Report{Root: abs, Findings: []Finding{}}
	wf := filepath.Join(abs, ".github", "workflows")
	// Ensure neither intermediate component is a symlink.
	for _, path := range []string{filepath.Join(abs, ".github"), wf} {
		st, err := os.Lstat(path)
		if errors.Is(err, os.ErrNotExist) {
			return report, nil
		}
		if err != nil {
			return report, fmt.Errorf("inspect workflow directory: %w", err)
		}
		if !st.IsDir() || st.Mode()&os.ModeSymlink != 0 {
			return report, errors.New("workflow directory must not be a symlink")
		}
	}
	folder, err := os.Open(wf)
	if err != nil {
		return report, err
	}
	entries, err := folder.ReadDir(maxWorkflows + 1)
	_ = folder.Close()
	if err != nil && !errors.Is(err, io.EOF) {
		return report, err
	}
	if len(entries) > maxWorkflows {
		report.Truncated = true
		entries = entries[:maxWorkflows]
	}
	sort.Slice(entries, func(i, j int) bool { return entries[i].Name() < entries[j].Name() })
	for _, entry := range entries {
		name := entry.Name()
		if !strings.HasSuffix(name, ".yml") && !strings.HasSuffix(name, ".yaml") {
			continue
		}
		relative := filepath.ToSlash(filepath.Join(".github", "workflows", name))
		if !entry.Type().IsRegular() {
			report.Skipped = append(report.Skipped, relative)
			continue
		}
		contents, err := readLimited(filepath.Join(wf, name))
		if err != nil {
			report.Skipped = append(report.Skipped, relative)
			continue
		}
		report.Workflows++
		for lineNumber, line := range strings.Split(string(contents), "\n") {
			trimmed := strings.TrimSpace(line)
			if strings.HasPrefix(trimmed, "#") {
				continue
			}
			match := usesPattern.FindStringSubmatch(line)
			if len(match) < 2 {
				continue
			}
			ref := strings.TrimSpace(match[1])
			// Local actions and docker:// images are not GitHub remote actions.
			if strings.HasPrefix(ref, "./") || strings.HasPrefix(ref, "docker://") {
				continue
			}
			at := strings.LastIndexByte(ref, '@')
			if at < 1 || at == len(ref)-1 || !strings.Contains(ref[:at], "/") {
				continue
			}
			report.Actions++
			if shaPattern.MatchString(ref[at+1:]) {
				report.ImmutableActions++
				continue
			}
			report.Findings = append(report.Findings, Finding{
				Code: "ACTION_MUTABLE_REF", Workflow: relative, Line: lineNumber + 1, Reference: ref,
				Message: "Remote GitHub Action uses a mutable reference rather than a 40-character commit SHA.",
				Remedy:  "Consider pinning to a verified full commit SHA; keep the version tag as a comment for maintainability.",
			})
		}
	}
	return report, nil
}
func readLimited(path string) ([]byte, error) {
	f, err := os.Open(path)
	if err != nil {
		return nil, err
	}
	defer f.Close()
	data, err := io.ReadAll(io.LimitReader(f, maxWorkflowBytes+1))
	if err != nil {
		return nil, err
	}
	if len(data) > maxWorkflowBytes {
		return nil, errors.New("workflow file too large")
	}
	return data, nil
}
