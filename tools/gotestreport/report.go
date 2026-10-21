package main

import (
	"bufio"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"sort"
	"strings"
)

const maxEventBytes = 2 << 20
const maxIdentities = 200000

type event struct {
	Action  string  `json:"Action"`
	Package string  `json:"Package"`
	ImportPath string `json:"ImportPath"`
	FailedBuild string `json:"FailedBuild"`
	Test    string  `json:"Test"`
	Elapsed float64 `json:"Elapsed"`
	// Intentionally discard Output: test logs may contain secrets.
}

type Failure struct {
	Package string `json:"package"`
	Test    string `json:"test,omitempty"`
	Kind    string `json:"kind"`
	Hint    string `json:"hint"`
}

type Report struct {
	Status             string    `json:"status"`
	Packages           int       `json:"packages"`
	PassedTests        int       `json:"passed_tests"`
	FailedTests        int       `json:"failed_tests"`
	SkippedTests       int       `json:"skipped_tests"`
	Failures           []Failure `json:"failures"`
	IncompletePackages []string  `json:"incomplete_packages"`
}

type packageState struct {
	terminal bool
	failed   bool
	failedBuild string
}

type testState struct {
	packageName string
	name        string
	action      string
}

// Analyze interprets go test -json NDJSON without running commands or echoing
// potentially secret-bearing test output. It recognizes only Go's documented
// terminal pass/fail/skip actions and treats missing terminal events as incomplete.
func Analyze(input io.Reader) (Report, error) {
	result := Report{Status: "empty", Failures: []Failure{}, IncompletePackages: []string{}}
	scanner := bufio.NewScanner(input)
	scanner.Buffer(make([]byte, 4096), maxEventBytes)
	pkgs := make(map[string]*packageState)
	tests := make(map[string]*testState)
	buildFailures := make(map[string]bool)
	line := 0
	for scanner.Scan() {
		line++
		raw := strings.TrimSpace(scanner.Text())
		if raw == "" {
			continue
		}
		var e event
		if err := json.Unmarshal([]byte(raw), &e); err != nil {
			return Report{}, fmt.Errorf("invalid go test JSON at event %d: %w", line, err)
		}
		// Go 1.24+ interleaves BuildEvent records without a Package field.
		// Build output is deliberately discarded to avoid leaking secrets.
		if e.Action == "build-output" || e.Action == "build-fail" {
			if e.ImportPath == "" || len(e.ImportPath) > 4096 {
				return Report{}, fmt.Errorf("invalid go build event at line %d", line)
			}
			if e.Action == "build-fail" { buildFailures[e.ImportPath] = true }
			continue
		}
		// A stream with other JSON records is not a trustworthy test report.
		if e.Package == "" || e.Action == "" || len(e.Package) > 4096 || len(e.Test) > 4096 {
			return Report{}, fmt.Errorf("invalid go test event at line %d (missing or oversized identity)", line)
		}
		pkg, found := pkgs[e.Package]
		if !found {
			if len(pkgs) >= maxIdentities {
				return Report{}, errors.New("too many packages")
			}
			pkg = &packageState{}
			pkgs[e.Package] = pkg
		}
		if e.Test == "" {
			switch e.Action {
			case "pass", "fail", "skip":
				pkg.terminal = true
				pkg.failed = e.Action == "fail"
				pkg.failedBuild = e.FailedBuild
			}
		} else {
			key := e.Package + "\x00" + e.Test
			test, found := tests[key]
			if !found {
				if len(tests) >= maxIdentities {
					return Report{}, errors.New("too many tests")
				}
				test = &testState{packageName: e.Package, name: e.Test}
				tests[key] = test
			}
			switch e.Action {
			case "pass", "fail", "skip":
				test.action = e.Action
			}
		}
	}
	if err := scanner.Err(); err != nil {
		return Report{}, fmt.Errorf("read go test stream: %w", err)
	}
	if len(pkgs) == 0 && len(buildFailures) == 0 {
		return Report{}, errors.New("no go test events found")
	}
	result.Packages = len(pkgs)
	for _, t := range tests {
		switch t.action {
		case "pass":
			result.PassedTests++
		case "skip":
			result.SkippedTests++
		case "fail":
			result.FailedTests++
			result.Failures = append(result.Failures, Failure{Package: t.packageName, Test: t.name, Kind: "test", Hint: "Rerun this test with go test -run using the exact test name in its package."})
		}
	}
	for name := range buildFailures {
		result.Failures = append(result.Failures, Failure{Package: name, Kind: "build", Hint: "Build failed; rerun go test for this package to inspect compiler diagnostics locally."})
	}
	for name, p := range pkgs {
		if !p.terminal {
			result.IncompletePackages = append(result.IncompletePackages, name)
		}
		if p.failed && !hasTestFailure(result.Failures, name) && (p.failedBuild == "" || !buildFailures[p.failedBuild]) {
			result.Failures = append(result.Failures, Failure{Package: name, Kind: "package", Hint: "Package build or setup failed; rerun go test for this package to inspect local diagnostics."})
		}
	}
	sort.Strings(result.IncompletePackages)
	sort.Slice(result.Failures, func(i, j int) bool {
		if result.Failures[i].Package == result.Failures[j].Package {
			return result.Failures[i].Test < result.Failures[j].Test
		}
		return result.Failures[i].Package < result.Failures[j].Package
	})
	if len(result.Failures) > 0 {
		result.Status = "failed"
	} else if len(result.IncompletePackages) > 0 {
		result.Status = "incomplete"
	} else {
		result.Status = "passed"
	}
	return result, nil
}

func hasTestFailure(failures []Failure, pkg string) bool {
	for _, failure := range failures {
		if failure.Package == pkg && failure.Kind == "test" {
			return true
		}
	}
	return false
}
