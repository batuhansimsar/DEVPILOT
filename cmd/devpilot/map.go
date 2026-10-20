package main

import (
	"encoding/json"
	"flag"
	"fmt"
	"io"
	"strings"

	"github.com/batuhansimsar/DEVPILOT/internal/workspace"
)

// runMap finds individual projects in a multi-project workspace without execution.
func runMap(args []string, stdout, stderr io.Writer) int {
	flags := flag.NewFlagSet("map", flag.ContinueOnError)
	flags.SetOutput(stderr)
	jsonOut := flags.Bool("json", false, "machine-readable workspace map")
	if err := flags.Parse(args); err != nil {
		return 2
	}
	if flags.NArg() > 1 {
		fmt.Fprintln(stderr, "map accepts at most one workspace path")
		return 2
	}
	root := "."
	if flags.NArg() == 1 {
		root = flags.Arg(0)
	}
	report, err := workspace.Discover(root)
	if err != nil {
		fmt.Fprintln(stderr, "map:", err)
		return 2
	}
	if *jsonOut {
		enc := json.NewEncoder(stdout)
		enc.SetIndent("", "  ")
		if err := enc.Encode(report); err != nil {
			fmt.Fprintln(stderr, "map:", err)
			return 2
		}
	} else {
		fmt.Fprintf(stdout, "DevPilot workspace map: %q\n", report.Workspace)
		fmt.Fprintf(stdout, "Projects: %d (scanned %d entries, skipped %d symlinks)\n", len(report.Projects), report.ScannedEntries, report.SkippedSymlinks)
		for _, project := range report.Projects {
			fmt.Fprintf(stdout, "  %q — %s [markers: %q]\n", project.Path, strings.Join(project.Report.Languages, ", "), strings.Join(project.Markers, ", "))
			if len(project.Report.Frameworks) > 0 {
				fmt.Fprintf(stdout, "    Frameworks: %s\n", strings.Join(project.Report.Frameworks, ", "))
			}
			if project.Report.Tests != nil {
				fmt.Fprintf(stdout, "    Suggested tests (not executed): %q %q\n", project.Report.Tests.Executable, project.Report.Tests.Arguments)
			}
			for _, f := range project.Report.Findings {
				if f.Level == "warning" {
					fmt.Fprintf(stdout, "    Warning: %q\n", f.Message)
					if f.Remedy != "" {
						fmt.Fprintf(stdout, "      Next: %q\n", f.Remedy)
					}
				}
			}
		}
		if report.Truncated {
			fmt.Fprintln(stdout, "WARNING: scan was truncated at a safety limit")
		}
		for _, s := range report.ScanErrors {
			fmt.Fprintf(stdout, "WARNING: %q\n", s)
		}
	}
	if report.Truncated || len(report.ScanErrors) > 0 {
		return 1
	}
	return 0
}
