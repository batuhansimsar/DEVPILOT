package main

import (
	"context"
	"encoding/json"
	"flag"
	"fmt"
	"io"
	"os"
	"strings"
	"time"

	"github.com/batuhansimsar/DEVPILOT/internal/doctor"
)

const usage = `DevPilot — understand and diagnose developer projects.

Usage:
  devpilot doctor [--path DIR] [--json] [--run-tests --trust-workspace] [--timeout 2m]
  devpilot version

The doctor command is read-only by default. Test execution is opt-in and
runs repository-controlled code; use it only for workspaces you trust.
`

var version = "dev"

func main() { os.Exit(run(os.Args[1:], os.Stdout, os.Stderr)) }

func run(args []string, out, stderr io.Writer) int {
	if len(args) == 0 {
		fmt.Fprint(out, usage)
		return 0
	}
	switch args[0] {
	case "-h", "--help", "help":
		fmt.Fprint(out, usage)
		return 0
	case "version", "--version":
		fmt.Fprintln(out, version)
		return 0
	case "doctor":
		return doctorCommand(args[1:], out, stderr)
	default:
		fmt.Fprintf(stderr, "Unknown command %q\n\n%s", args[0], usage)
		return 2
	}
}

func doctorCommand(args []string, out, stderr io.Writer) int {
	flags := flag.NewFlagSet("doctor", flag.ContinueOnError)
	flags.SetOutput(stderr)
	root := flags.String("path", ".", "workspace directory")
	jsonMode := flags.Bool("json", false, "write a machine-readable JSON report")
	runTests := flags.Bool("run-tests", false, "execute discovered test commands")
	trust := flags.Bool("trust-workspace", false, "acknowledge that test commands can execute arbitrary workspace code")
	timeout := flags.Duration("timeout", 2*time.Minute, "maximum duration of each test command")
	if err := flags.Parse(args); err != nil {
		return 2
	}
	if flags.NArg() > 0 {
		fmt.Fprintln(stderr, "Unexpected positional arguments:", strings.Join(flags.Args(), " "))
		return 2
	}
	if *timeout <= 0 {
		fmt.Fprintln(stderr, "--timeout must be positive")
		return 2
	}
	report, err := doctor.Analyze(context.Background(), *root, doctor.Options{RunTests: *runTests, TrustWorkspace: *trust, Timeout: *timeout})
	if err != nil {
		fmt.Fprintln(stderr, "devpilot:", err)
		return 2
	}
	if *jsonMode {
		encoder := json.NewEncoder(out)
		encoder.SetIndent("", "  ")
		if err := encoder.Encode(report); err != nil {
			fmt.Fprintln(stderr, "devpilot:", err)
			return 2
		}
	} else {
		fmt.Fprintf(out, "DevPilot doctor — %s\n\n", report.Workspace)
		if len(report.Detections) == 0 {
			fmt.Fprintln(out, "Detected: no supported project manifests")
		}
		for _, d := range report.Detections {
			fmt.Fprintf(out, "  [detected] %s (%s: %s)\n", d.Name, d.Kind, strings.Join(d.Evidence, ", "))
		}
		fmt.Fprintln(out)
		for _, f := range report.Findings {
			fmt.Fprintf(out, "  [%s] %s: %s\n", strings.ToUpper(string(f.Severity)), f.Code, f.Message)
			if len(f.Evidence) > 0 {
				fmt.Fprintf(out, "    Evidence: %s\n", strings.Join(f.Evidence, ", "))
			}
			if f.Remedy != "" {
				fmt.Fprintf(out, "    Next: %s\n", f.Remedy)
			}
		}
		if len(report.TestCommands) > 0 {
			fmt.Fprintln(out, "\nDiscovered test commands (not executed unless --run-tests is set):")
			for _, t := range report.TestCommands {
				fmt.Fprintf(out, "  %s: %s %s\n", t.Directory, t.Executable, strings.Join(t.Arguments, " "))
			}
		}
		for _, r := range report.TestResults {
			outcome := "PASS"
			if !r.Passed {
				outcome = "FAIL"
			}
			fmt.Fprintf(out, "\nTest result [%s] %s: %s %s\n", outcome, r.Command.Directory, r.Command.Executable, strings.Join(r.Command.Arguments, " "))
			if r.Output != "" {
				fmt.Fprintln(out, r.Output)
			}
		}
	}
	for _, f := range report.Findings {
		if f.Severity == doctor.Error {
			return 1
		}
	}
	return 0
}
