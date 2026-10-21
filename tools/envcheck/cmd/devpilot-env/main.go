package main

import (
	"encoding/json"
	"errors"
	"flag"
	"fmt"
	"io"
	"os"
	"strconv"
	"strings"

	"github.com/batuhansimsar/DEVPILOT/tools/envcheck/internal/envcheck"
)

func main() {
	os.Exit(run(os.Args[1:], os.Stdout, os.Stderr))
}

func run(args []string, out, errOut io.Writer) int {
	flags := flag.NewFlagSet("devpilot-env", flag.ContinueOnError)
	flags.SetOutput(errOut)
	path := flags.String("path", ".", "project root to inspect")
	jsonOutput := flags.Bool("json", false, "write machine-readable JSON")
	strict := flags.Bool("strict", false, "exit 1 if documented variables are unconfigured")
	flags.Usage = func() {
		fmt.Fprintln(errOut, "Usage: devpilot-env [--path DIR] [--json] [--strict]")
		fmt.Fprintln(errOut, "Read-only environment template audit. No secret values are printed.")
		flags.PrintDefaults()
	}
	if err := flags.Parse(args); err != nil {
		if errors.Is(err, flag.ErrHelp) {
			return 0
		}
		return 2
	}
	if flags.NArg() != 0 {
		fmt.Fprintln(errOut, "error: unexpected positional arguments")
		return 2
	}
	report, err := envcheck.Check(*path, os.LookupEnv)
	if err != nil {
		fmt.Fprintln(errOut, "error:", err)
		return 2
	}
	if *jsonOutput {
		enc := json.NewEncoder(out)
		enc.SetIndent("", "  ")
		if err := enc.Encode(report); err != nil {
			fmt.Fprintln(errOut, "error: write report:", err)
			return 2
		}
	} else {
		fmt.Fprintf(out, "DevPilot environment audit\nProject: %s\n", strconv.QuoteToASCII(report.Project))
		if len(report.TemplateFiles) == 0 {
			fmt.Fprintln(out, "No root-level .env template files found.")
		} else {
			quotedNames := make([]string, len(report.TemplateFiles))
			for i, name := range report.TemplateFiles {
				quotedNames[i] = strconv.QuoteToASCII(name)
			}
			fmt.Fprintf(out, "Templates: %s\n", strings.Join(quotedNames, ", "))
			for _, v := range report.Variables {
				fmt.Fprintf(out, "  %-14s %s\n", v.Status, v.Name)
			}
			fmt.Fprintf(out, "Documented: %d | Process: %d | .env: %d | Unconfigured: %d\n",
				report.Summary.Total, report.Summary.InProcess, report.Summary.InDotEnv, report.Summary.Unconfigured)
		}
		fmt.Fprintln(out, "Only variable names and configuration evidence are reported; values are never printed.")
	}
	if *strict && report.Summary.Unconfigured > 0 {
		return 1
	}
	return 0
}
