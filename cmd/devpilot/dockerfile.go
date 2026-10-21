package main

import (
	"encoding/json"
	"flag"
	"fmt"
	"io"
	"strings"

	"github.com/batuhansimsar/DEVPILOT/internal/dockerfile"
)

// dockerfileCommand statically inspects an untrusted Dockerfile without running Docker.
func dockerfileCommand(args []string, stdout, stderr io.Writer) int {
	flags := flag.NewFlagSet("dockerfile", flag.ContinueOnError)
	flags.SetOutput(stderr)
	jsonOut := flags.Bool("json", false, "machine-readable JSON report")
	if err := flags.Parse(args); err != nil {
		return 2
	}
	if flags.NArg() > 1 {
		fmt.Fprintln(stderr, "dockerfile accepts at most one project directory")
		return 2
	}
	path := "."
	if flags.NArg() == 1 {
		path = flags.Arg(0)
	}
	report, err := dockerfile.Inspect(path)
	if err != nil {
		fmt.Fprintln(stderr, "dockerfile:", err)
		return 2
	}
	if *jsonOut {
		enc := json.NewEncoder(stdout)
		enc.SetIndent("", "  ")
		if err := enc.Encode(report); err != nil {
			fmt.Fprintln(stderr, err)
			return 2
		}
	} else {
		fmt.Fprintf(stdout, "DevPilot Dockerfile: %s\n", report.File)
		for _, stage := range report.Stages {
			fmt.Fprintf(stdout, "Stage at line %d: %s\n", stage.Line, stage.Base)
		}
		if len(report.Findings) == 0 {
			fmt.Fprintln(stdout, "No findings from the available static checks.")
		}
		for _, f := range report.Findings {
			fmt.Fprintf(stdout, "[%s] %s: %s\n", strings.ToUpper(f.Level), f.Evidence, f.Message)
			fmt.Fprintf(stdout, "       Next: %s\n", f.Remedy)
		}
	}
	if report.HasWarnings() {
		return 1
	}
	return 0
}
