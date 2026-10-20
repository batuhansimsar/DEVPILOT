// Package dockerfile performs bounded, read-only checks on a project's Dockerfile.
// These are static heuristics, not build or runtime verification.
package dockerfile

import (
	"bufio"
	"bytes"
	"errors"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"regexp"
	"sort"
	"strings"
)

const limit = 1024 * 1024

var remoteShell = regexp.MustCompile(`(?i)\b(?:curl|wget)\b[^\n]*\|[[:space:]]*(?:(?:/bin/)?(?:ba)?sh)\b`)

type Finding struct {
	Level    string `json:"level"`
	Code     string `json:"code"`
	Message  string `json:"message"`
	Evidence string `json:"evidence"`
	Remedy   string `json:"remedy"`
}

type Stage struct {
	Base string `json:"base"`
	Name string `json:"name,omitempty"`
	Line int    `json:"line"`
}

type Report struct {
	File     string    `json:"file"`
	Stages   []Stage   `json:"stages"`
	Findings []Finding `json:"findings"`
}

func (r Report) HasWarnings() bool {
	for _, f := range r.Findings {
		if f.Level == "warning" {
			return true
		}
	}
	return false
}

// readRegular refuses non-regular files including symlinks and enforces a hard
// byte limit. It is not a sandbox against concurrent filesystem mutations.
func readRegular(path string) ([]byte, error) {
	stat, err := os.Lstat(path)
	if err != nil {
		return nil, err
	}
	if !stat.Mode().IsRegular() {
		return nil, errors.New("not a regular file (symlinks refused)")
	}
	if stat.Size() > limit {
		return nil, fmt.Errorf("file exceeds %d byte limit", limit)
	}
	f, err := os.Open(path)
	if err != nil {
		return nil, err
	}
	defer f.Close()
	data, err := io.ReadAll(io.LimitReader(f, limit+1))
	if err != nil {
		return nil, err
	}
	if len(data) > limit {
		return nil, fmt.Errorf("file exceeds %d byte limit", limit)
	}
	return data, nil
}

// Inspect analyzes only Dockerfile and .dockerignore at the project root.
// It never invokes Docker, executes shell commands, or evaluates build stages.
func Inspect(root string) (Report, error) {
	abs, err := filepath.Abs(root)
	if err != nil {
		return Report{}, err
	}
	stat, err := os.Stat(abs)
	if err != nil {
		return Report{}, err
	}
	if !stat.IsDir() {
		return Report{}, errors.New("project path must be a directory")
	}
	data, err := readRegular(filepath.Join(abs, "Dockerfile"))
	if err != nil {
		return Report{}, fmt.Errorf("Dockerfile: %w", err)
	}
	r := Report{File: filepath.Join(abs, "Dockerfile"), Stages: []Stage{}, Findings: []Finding{}}
	add := func(level, code, message string, line int, remedy string) {
		r.Findings = append(r.Findings, Finding{level, code, message, fmt.Sprintf("Dockerfile:%d", line), remedy})
	}
	stageNames := map[string]bool{}
	lastUser := ""
	lastUserLine := 0
	copyAll := []int{}
	lines := logicalLines(data)
	for _, l := range lines {
		parts := strings.Fields(l.Text)
		if len(parts) == 0 {
			continue
		}
		instruction := strings.ToUpper(parts[0])
		body := strings.TrimSpace(l.Text[len(parts[0]):])
		switch instruction {
		case "FROM":
			words := strings.Fields(body)
			start := 0
			for start < len(words) && strings.HasPrefix(words[start], "--") {
				start++
			}
			if start >= len(words) {
				add("warning", "invalid-from", "FROM has no recognizable base image", l.Line, "Specify an image or previous build stage")
				continue
			}
			base := words[start]
			name := ""
			if len(words) >= start+3 && strings.EqualFold(words[start+1], "AS") {
				name = words[start+2]
			}
			r.Stages = append(r.Stages, Stage{Base: base, Name: name, Line: l.Line})
			if !stageNames[strings.ToLower(base)] && base != "scratch" && !strings.ContainsAny(base, "${}") && !strings.Contains(base, "@sha256:") {
				add("warning", "mutable-base-image", "Base image is not pinned to an immutable digest: "+base, l.Line, "Prefer an image digest for reproducible builds; verify digest updates regularly")
			}
			if name != "" {
				stageNames[strings.ToLower(name)] = true
			}
			lastUser = ""
			lastUserLine = 0
		case "USER":
			lastUser = strings.TrimSpace(body)
			lastUserLine = l.Line
		case "COPY", "ADD":
			if copyEntireContext(body) {
				copyAll = append(copyAll, l.Line)
			}
			if instruction == "ADD" && (strings.Contains(body, "https://") || strings.Contains(body, "http://")) && !strings.Contains(body, "--checksum=") {
				add("info", "remote-add", "ADD downloads a remote resource without an explicit checksum in this instruction", l.Line, "Consider a checksum-pinned download, or verify the content independently")
			}
		case "RUN":
			if remoteShell.MatchString(body) {
				add("warning", "remote-script-shell", "RUN appears to pipe downloaded content directly into a shell", l.Line, "Download and verify artifacts before executing them")
			}
		}
	}
	if len(r.Stages) == 0 {
		add("warning", "missing-from", "No FROM instruction found", 1, "Add a valid FROM instruction for a build stage")
	}
	if strings.EqualFold(lastUser, "root") || lastUser == "0" || lastUser == "0:0" {
		add("info", "explicit-root-user", "Final stage explicitly selects the root user", lastUserLine, "Use a non-root runtime user when the application permits it")
	}
	ignorePath := filepath.Join(abs, ".dockerignore")
	_, err = os.Lstat(ignorePath)
	if errors.Is(err, os.ErrNotExist) && len(copyAll) > 0 {
		add("warning", "missing-dockerignore", "The build copies the entire context without a .dockerignore file", copyAll[0], "Add .dockerignore to exclude secrets, local caches, and build artifacts")
	} else if err == nil {
		if _, err := readRegular(ignorePath); err != nil {
			r.Findings = append(r.Findings, Finding{"info", "unreadable-dockerignore", "Could not inspect .dockerignore", ".dockerignore", "Review the .dockerignore file type and size"})
		}
	}
	sort.SliceStable(r.Findings, func(i, j int) bool {
		return r.Findings[i].Evidence < r.Findings[j].Evidence || (r.Findings[i].Evidence == r.Findings[j].Evidence && r.Findings[i].Code < r.Findings[j].Code)
	})
	return r, nil
}

type logicalLine struct {
	Line int
	Text string
}

func logicalLines(data []byte) []logicalLine {
	scanner := bufio.NewScanner(bytes.NewReader(data))
	scanner.Buffer(make([]byte, 4096), limit+1)
	out := []logicalLine{}
	current := ""
	begin := 0
	lineNo := 0
	for scanner.Scan() {
		lineNo++
		raw := strings.TrimSpace(scanner.Text())
		if current == "" {
			begin = lineNo
		}
		if raw == "" || (strings.HasPrefix(raw, "#") && current == "") {
			continue
		}
		continuation := strings.HasSuffix(raw, `\`)
		if continuation {
			raw = strings.TrimSuffix(raw, `\`)
		}
		current += raw + " "
		if !continuation {
			out = append(out, logicalLine{begin, strings.TrimSpace(current)})
			current = ""
		}
	}
	if current != "" {
		out = append(out, logicalLine{begin, strings.TrimSpace(current)})
	}
	return out
}

func copyEntireContext(body string) bool {
	// JSON-array syntax is intentionally not inferred; avoid false positives.
	if strings.HasPrefix(strings.TrimSpace(body), "[") {
		return false
	}
	args := strings.Fields(body)
	nonFlag := []string{}
	for _, v := range args {
		if !strings.HasPrefix(v, "--") {
			nonFlag = append(nonFlag, v)
		}
	}
	return len(nonFlag) >= 2 && nonFlag[0] == "."
}
