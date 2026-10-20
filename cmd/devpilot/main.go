package main

import (
	"encoding/json"
	"errors"
	"flag"
	"fmt"
	"io"
	"os"
	"strings"
	"time"

	"github.com/batuhansimsar/DEVPILOT/internal/doctor"
	"github.com/batuhansimsar/DEVPILOT/internal/runner"
)

func main() { os.Exit(run(os.Args[1:], os.Stdout, os.Stderr)) }
func run(args []string, stdout, stderr io.Writer) int {
	if len(args) == 0 {
		usage(stdout)
		return 0
	}
	switch args[0] {
	case "help", "--help", "-h":
		usage(stdout)
		return 0
	case "version", "--version":
		fmt.Fprintln(stdout, "devpilot 0.1.0")
		return 0
	case "doctor":
		flags := flag.NewFlagSet("doctor", flag.ContinueOnError)
		flags.SetOutput(stderr)
		path := flags.String("path", ".", "workspace to analyze")
		jsonOut := flags.Bool("json", false, "emit machine-readable report")
		if err := flags.Parse(args[1:]); err != nil {
			return 2
		}
		if flags.NArg() != 0 {
			fmt.Fprintln(stderr, "doctor: unexpected arguments")
			return 2
		}
		report, err := doctor.Analyze(*path)
		if err != nil {
			fmt.Fprintln(stderr, "doctor:", err)
			return 1
		}
		if *jsonOut {
			enc := json.NewEncoder(stdout)
			enc.SetIndent("", "  ")
			if err := enc.Encode(report); err != nil {
				fmt.Fprintln(stderr, err)
				return 1
			}
		} else {
			printReport(stdout, report)
		}
		return 0
	case "test":
		flags := flag.NewFlagSet("test", flag.ContinueOnError)
		flags.SetOutput(stderr)
		path := flags.String("path", ".", "workspace to inspect")
		runID := flags.String("run", "", "run discovered test ID")
		trust := flags.Bool("trust", false, "explicitly authorize executing repository code")
		timeout := flags.Duration("timeout", 2*time.Minute, "test timeout (max 30m)")
		if err := flags.Parse(args[1:]); err != nil {
			return 2
		}
		if flags.NArg() != 0 {
			fmt.Fprintln(stderr, "test: unexpected arguments")
			return 2
		}
		report, err := doctor.Analyze(*path)
		if err != nil {
			fmt.Fprintln(stderr, "test:", err)
			return 1
		}
		if *runID == "" {
			if len(report.Tests) == 0 {
				fmt.Fprintln(stdout, "No tests discovered.")
			}
			for _, t := range report.Tests {
				fmt.Fprintf(stdout, "%s  (%s)  %s %s\n", t.ID, t.Directory, t.Program, strings.Join(t.Args, " "))
			}
			fmt.Fprintln(stdout, "To execute: devpilot test --run <ID> --trust")
			return 0
		}
		for _, t := range report.Tests {
			if t.ID == *runID {
				if !*trust {
					fmt.Fprintln(stderr, "Refusing to execute repository code without --trust")
					return 2
				}
				result, e := runner.Run(report.Root, t, *trust, *timeout)
				if result.Output != "" {
					fmt.Fprint(stdout, result.Output)
					if !strings.HasSuffix(result.Output, "\n") {
						fmt.Fprintln(stdout)
					}
				}
				if result.Truncated {
					fmt.Fprintln(stdout, "[output truncated to 512 KiB]")
				}
				if e != nil {
					fmt.Fprintln(stderr, "test:", e)
					return 1
				}
				fmt.Fprintf(stdout, "PASS %s (%s)\n", t.ID, result.Duration.Round(time.Millisecond))
				return 0
			}
		}
		fmt.Fprintf(stderr, "Unknown test ID %q; run 'devpilot test' to list available targets\n", *runID)
		return 2
	default:
		fmt.Fprintf(stderr, "Unknown command %q\n", args[0])
		usage(stderr)
		return 2
	}
}
func usage(w io.Writer) {
	fmt.Fprintln(w, `DevPilot — read-only project diagnostics and opt-in test runner

Usage:
  devpilot doctor [--path DIR] [--json]
  devpilot test [--path DIR]                  List discovered tests
  devpilot test [--path DIR] --run ID --trust [--timeout 2m]
  devpilot version

DevPilot never executes project code during 'doctor'. Test execution needs --trust.`)
}
func printReport(w io.Writer, r doctor.Report) {
	fmt.Fprintf(w, "DevPilot doctor — %s\n", r.Root)
	if r.Git.IsRepository {
		fmt.Fprintf(w, "Git: branch %s\n", fallback(r.Git.Branch, "detached or unknown"))
	} else {
		fmt.Fprintln(w, "Git: not detected")
	}
	fmt.Fprintf(w, "Projects (%d):\n", len(r.Projects))
	for _, p := range r.Projects {
		fmt.Fprintf(w, "  %s — %s", p.Directory, strings.Join(p.Languages, ", "))
		if len(p.Frameworks) > 0 {
			fmt.Fprintf(w, " [%s]", strings.Join(p.Frameworks, ", "))
		}
		fmt.Fprintln(w)
	}
	fmt.Fprintf(w, "Tests (%d):\n", len(r.Tests))
	for _, t := range r.Tests {
		fmt.Fprintf(w, "  %s: %s %s\n", t.ID, t.Program, strings.Join(t.Args, " "))
	}
	fmt.Fprintf(w, "Findings (%d):\n", len(r.Findings))
	for _, f := range r.Findings {
		fmt.Fprintf(w, "  [%s] %s — %s\n", strings.ToUpper(f.Level), f.Code, f.Message)
		if f.Evidence != "" {
			fmt.Fprintf(w, "    Evidence: %s\n", f.Evidence)
		}
		if f.Remedy != "" {
			fmt.Fprintf(w, "    Next: %s\n", f.Remedy)
		}
	}
}
func fallback(s, alt string) string {
	if s == "" {
		return alt
	}
	return s
}

var _ = errors.Is
