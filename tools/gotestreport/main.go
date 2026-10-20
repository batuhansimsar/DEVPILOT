// DevPilot Go Test Report summarizes go test -json without executing tests.
package main

import (
	"encoding/json"
	"flag"
	"fmt"
	"io"
	"os"
)

func run(args []string, stdin io.Reader, stdout, stderr io.Writer) int {
	flags := flag.NewFlagSet("gotestreport", flag.ContinueOnError)
	flags.SetOutput(stderr)
	file := flags.String("input", "-", "go test -json NDJSON file, or - for stdin")
	format := flags.String("format", "text", "output format: text or json")
	if err := flags.Parse(args); err != nil {
		if err == flag.ErrHelp {
			return 0
		}
		return 2
	}
	if flags.NArg() != 0 || (*format != "text" && *format != "json") {
		fmt.Fprintln(stderr, "usage: gotestreport [-input PATH|-] [-format text|json]")
		return 2
	}
	reader := stdin
	if *file != "-" {
		f, err := os.Open(*file)
		if err != nil {
			fmt.Fprintf(stderr, "open input: %v\n", err)
			return 2
		}
		defer f.Close()
		reader = f
	}
	report, err := Analyze(reader)
	if err != nil {
		fmt.Fprintf(stderr, "test report: %v\n", err)
		return 2
	}
	if *format == "json" {
		encoder := json.NewEncoder(stdout)
		encoder.SetIndent("", "  ")
		if err := encoder.Encode(report); err != nil {
			fmt.Fprintf(stderr, "output: %v\n", err)
			return 2
		}
	} else {
		fmt.Fprintf(stdout, "DevPilot Go Test Report: %s\n", report.Status)
		fmt.Fprintf(stdout, "Packages: %d | Tests passed: %d, failed: %d, skipped: %d\n", report.Packages, report.PassedTests, report.FailedTests, report.SkippedTests)
		for _, failure := range report.Failures {
			fmt.Fprintf(stdout, "FAIL %q", failure.Package)
			if failure.Test != "" {
				fmt.Fprintf(stdout, " test %q", failure.Test)
			}
			fmt.Fprintf(stdout, " — %s\n", failure.Hint)
		}
		for _, name := range report.IncompletePackages {
			fmt.Fprintf(stdout, "INCOMPLETE %q — no package terminal event; check for truncated stream.\n", name)
		}
		fmt.Fprintln(stdout, "Note: raw test output is intentionally omitted because it may contain secrets.")
	}
	if report.Status == "failed" {
		return 1
	}
	if report.Status == "incomplete" {
		return 2
	}
	return 0
}

func main() { os.Exit(run(os.Args[1:], os.Stdin, os.Stdout, os.Stderr)) }
