package main

import (
	"encoding/json"
	"flag"
	"fmt"
	"io"
	"strconv"

	"github.com/batuhansimsar/DEVPILOT/internal/ciaudit"
)

func ciAuditCommand(args []string, stdout, stderr io.Writer) int {
	flags := flag.NewFlagSet("ci-audit", flag.ContinueOnError)
	flags.SetOutput(stderr)
	jsonOutput := flags.Bool("json", false, "machine-readable report")
	if err := flags.Parse(args); err != nil {
		return 2
	}
	if flags.NArg() > 1 {
		fmt.Fprintln(stderr, "ci-audit accepts at most one path")
		return 2
	}
	path := "."
	if flags.NArg() == 1 {
		path = flags.Arg(0)
	}
	report, err := ciaudit.Inspect(path)
	if err != nil {
		fmt.Fprintln(stderr, "ci-audit:", err)
		return 2
	}
	if *jsonOutput {
		encoder := json.NewEncoder(stdout)
		encoder.SetIndent("", "  ")
		if err := encoder.Encode(report); err != nil {
			fmt.Fprintln(stderr, err)
			return 2
		}
	} else {
		fmt.Fprintf(stdout, "DevPilot CI audit: %d workflow(s), %d remote action(s), %d pinned to SHA.\n", report.Workflows, report.Actions, report.ImmutableActions)
		for _, f := range report.Findings {
			fmt.Fprintf(stdout, "[WARN] %s:%d: %s\n", strconv.Quote(f.Workflow), f.Line, strconv.Quote(f.Reference))
			fmt.Fprintln(stdout, "       ", f.Remedy)
		}
		for _, path := range report.Skipped {
			fmt.Fprintf(stderr, "Could not read workflow: %s\n", strconv.Quote(path))
		}
		if report.Truncated {
			fmt.Fprintln(stderr, "Workflow scan was truncated by a safety limit.")
		}
	}
	if report.Truncated || len(report.Skipped) > 0 || len(report.Findings) > 0 {
		return 1
	}
	return 0
}
