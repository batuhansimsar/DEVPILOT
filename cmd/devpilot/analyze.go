package main

import (
	"encoding/json"
	"flag"
	"fmt"
	"io"

	"github.com/batuhansimsar/DEVPILOT/internal/analyze"
)

// analyzeCommand never invokes tools, project scripts, or shells.
func analyzeCommand(args []string, stdout, stderr io.Writer) int {
	flags := flag.NewFlagSet("analyze", flag.ContinueOnError)
	flags.SetOutput(stderr)
	jsonOut := flags.Bool("json", false, "machine-readable inventory")
	if err := flags.Parse(args); err != nil {
		return 2
	}
	if flags.NArg() > 1 {
		fmt.Fprintln(stderr, "analyze accepts at most one path")
		return 2
	}
	path := "."
	if flags.NArg() == 1 {
		path = flags.Arg(0)
	}
	report, err := analyze.Inspect(path)
	if err != nil {
		fmt.Fprintln(stderr, "analyze:", err)
		return 2
	}
	if *jsonOut {
		encoder := json.NewEncoder(stdout)
		encoder.SetIndent("", "  ")
		if err := encoder.Encode(report); err != nil {
			fmt.Fprintln(stderr, "analyze:", err)
			return 2
		}
	} else {
		fmt.Fprintf(stdout, "DevPilot analyze: %s\nFiles: %d", report.Path, report.FileCount)
		if report.Truncated {
			fmt.Fprint(stdout, " (scan limit reached)")
		}
		fmt.Fprintln(stdout)
		for _, lang := range report.Languages {
			fmt.Fprintf(stdout, "  %s: %d files\n", lang.Name, lang.Files)
		}
		for _, marker := range report.Manifests {
			fmt.Fprintln(stdout, "  Manifest:", marker)
		}
		for _, ci := range report.CI {
			fmt.Fprintln(stdout, "  CI:", ci)
		}
		for _, config := range report.Containers {
			fmt.Fprintln(stdout, "  Container:", config)
		}
		for _, warning := range report.Warnings {
			fmt.Fprintln(stderr, "Warning:", warning)
		}
	}
	if report.Truncated || len(report.Warnings) > 0 {
		return 1
	}
	return 0
}
