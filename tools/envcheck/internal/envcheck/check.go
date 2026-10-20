// Package envcheck compares documented dotenv variable names to local evidence
// without exposing credential values or executing workspace code.
package envcheck

import (
	"bufio"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"sort"
	"strings"
)

const maxFileSize = 1 << 20 // Untrusted configuration files are limited to 1 MiB.

type Status string

const (
	InProcess    Status = "in_process"
	InDotEnv     Status = "in_dotenv"
	Unconfigured Status = "unconfigured"
)

// Variable contains names and evidence only. Never add parsed values to this type.
type Variable struct {
	Name      string   `json:"name"`
	Templates []string `json:"templates"`
	Status    Status   `json:"status"`
}

type Summary struct {
	Total        int `json:"total"`
	InProcess    int `json:"in_process"`
	InDotEnv     int `json:"in_dotenv"`
	Unconfigured int `json:"unconfigured"`
}

type Report struct {
	Project       string     `json:"project"`
	TemplateFiles []string   `json:"template_files"`
	Variables     []Variable `json:"variables"`
	Summary       Summary    `json:"summary"`
}

// Check inspects a project's root-level environment templates and .env file.
// A variable in .env is evidence of configuration, not proof that the project loads it.
// lookup allows callers to check their process environment without including values
// in Report. No project code or shell commands are executed.
func Check(root string, lookup func(string) (string, bool)) (Report, error) {
	if lookup == nil {
		lookup = os.LookupEnv
	}
	abs, err := filepath.Abs(root)
	if err != nil {
		return Report{}, fmt.Errorf("resolve project path: %w", err)
	}
	info, err := os.Stat(abs)
	if err != nil {
		return Report{}, fmt.Errorf("inspect project path: %w", err)
	}
	if !info.IsDir() {
		return Report{}, fmt.Errorf("project path %q is not a directory", abs)
	}
	entries, err := os.ReadDir(abs)
	if err != nil {
		return Report{}, fmt.Errorf("list project directory: %w", err)
	}
	templates := make(map[string][]string)
	templateFiles := make([]string, 0)
	for _, entry := range entries {
		name := entry.Name()
		if !isTemplate(name) || !entry.Type().IsRegular() {
			continue // Never follow symlinks in untrusted workspaces.
		}
		found, err := readAssignments(filepath.Join(abs, name))
		if err != nil {
			return Report{}, fmt.Errorf("inspect %q: %w", name, err)
		}
		templateFiles = append(templateFiles, name)
		for key := range found {
			templates[key] = append(templates[key], name)
		}
	}
	sort.Strings(templateFiles)
	configured := make(map[string]bool)
	// .env is deliberately the only on-disk configuration source we inspect.
	// Environment-specific files should be handled explicitly by users.
	if info, err := os.Lstat(filepath.Join(abs, ".env")); err == nil {
		if info.Mode().IsRegular() {
			configured, err = readAssignments(filepath.Join(abs, ".env"))
			if err != nil {
				return Report{}, fmt.Errorf("inspect .env: %w", err)
			}
		}
	} else if !os.IsNotExist(err) {
		return Report{}, fmt.Errorf("inspect .env: %w", err)
	}

	report := Report{
		Project: abs, TemplateFiles: templateFiles, Variables: make([]Variable, 0, len(templates)),
	}
	keys := make([]string, 0, len(templates))
	for name := range templates {
		keys = append(keys, name)
	}
	sort.Strings(keys)
	for _, name := range keys {
		v := Variable{Name: name, Templates: templates[name]}
		if value, ok := lookup(name); ok && strings.TrimSpace(value) != "" {
			v.Status = InProcess
			report.Summary.InProcess++
		} else if configured[name] {
			v.Status = InDotEnv
			report.Summary.InDotEnv++
		} else {
			v.Status = Unconfigured
			report.Summary.Unconfigured++
		}
		report.Variables = append(report.Variables, v)
	}
	report.Summary.Total = len(keys)
	return report, nil
}

func isTemplate(name string) bool {
	if !strings.HasPrefix(name, ".env.") {
		return false
	}
	for _, suffix := range []string{".example", ".sample", ".template"} {
		if strings.HasSuffix(name, suffix) || name == ".env"+suffix {
			return true
		}
	}
	return false
}

// readAssignments returns only names and whether their values are nonempty.
func readAssignments(path string) (map[string]bool, error) {
	f, err := os.Open(path)
	if err != nil {
		return nil, err
	}
	defer f.Close()
	data, err := io.ReadAll(io.LimitReader(f, maxFileSize+1))
	if err != nil {
		return nil, err
	}
	if len(data) > maxFileSize {
		return nil, fmt.Errorf("file exceeds 1 MiB limit")
	}
	vars := make(map[string]bool)
	scanner := bufio.NewScanner(strings.NewReader(string(data)))
	scanner.Buffer(make([]byte, 4096), maxFileSize+1)
	for scanner.Scan() {
		name, val, ok := parseAssignment(scanner.Text())
		if !ok {
			continue
		}
		vars[name] = vars[name] || hasValue(val)
	}
	if err := scanner.Err(); err != nil {
		return nil, err
	}
	return vars, nil
}

func parseAssignment(line string) (string, string, bool) {
	line = strings.TrimSpace(line)
	if line == "" || strings.HasPrefix(line, "#") {
		return "", "", false
	}
	if strings.HasPrefix(line, "export ") || strings.HasPrefix(line, "export\t") {
		line = strings.TrimSpace(strings.TrimPrefix(line, "export"))
	}
	idx := strings.IndexByte(line, '=')
	if idx <= 0 {
		return "", "", false
	}
	name := strings.TrimSpace(line[:idx])
	if !validName(name) {
		return "", "", false
	}
	return name, strings.TrimSpace(line[idx+1:]), true
}

func validName(s string) bool {
	if s == "" {
		return false
	}
	for i, r := range s {
		if r == '_' || r >= 'A' && r <= 'Z' || r >= 'a' && r <= 'z' {
			continue
		}
		if i > 0 && r >= '0' && r <= '9' {
			continue
		}
		return false
	}
	return true
}

func hasValue(s string) bool {
	s = strings.TrimSpace(s)
	if s == "" || strings.HasPrefix(s, "#") {
		return false
	}
	if s[0] == '\'' || s[0] == '"' {
		// Only a closed quoted value is considered configured. A trailing comment
		// does not count as part of the value.
		end := strings.IndexByte(s[1:], s[0])
		return end >= 0 && strings.TrimSpace(s[1:1+end]) != ""
	}
	// Unquoted dotenv comments start after whitespace, not inside URLs/tokens.
	for i := 1; i < len(s); i++ {
		if s[i] == '#' && (s[i-1] == ' ' || s[i-1] == '\t') {
			s = s[:i]
			break
		}
	}
	return strings.TrimSpace(s) != ""
}
