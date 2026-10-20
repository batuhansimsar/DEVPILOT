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
	"github.com/batuhansimsar/DEVPILOT/internal/runner"
)

func main() { os.Exit(run(os.Args[1:], os.Stdout, os.Stderr)) }

func run(args []string, out, errOut io.Writer) int {
	if len(args) == 0 || args[0] == "help" || args[0] == "--help" {
		usage(out)
		return 0
	}
	switch args[0] {
	case "doctor":
		f := flag.NewFlagSet("doctor", flag.ContinueOnError)
		f.SetOutput(errOut)
		asJSON := f.Bool("json", false, "print machine-readable JSON")
		if err := f.Parse(args[1:]); err != nil {
			return 2
		}
		path, ok := workspaceArg(f.Args(), errOut)
		if !ok {
			return 2
		}
		r, err := doctor.Inspect(path)
		if err != nil {
			fmt.Fprintln(errOut, "doctor:", err)
			return 1
		}
		if *asJSON {
			enc := json.NewEncoder(out)
			enc.SetIndent("", "  ")
			if err := enc.Encode(r); err != nil {
				fmt.Fprintln(errOut, err)
				return 1
			}
		} else {
			display(out, r)
		}
		for _, finding := range r.Findings {
			if finding.Severity == "error" {
				return 1
			}
		}
		return 0
	case "test":
		f := flag.NewFlagSet("test", flag.ContinueOnError)
		f.SetOutput(errOut)
		trusted := f.Bool("trust", false, "allow project test commands to execute")
		timeout := f.Duration("timeout", 90*time.Second, "test timeout")
		if err := f.Parse(args[1:]); err != nil {
			return 2
		}
		path, ok := workspaceArg(f.Args(), errOut)
		if !ok {
			return 2
		}
		// Trust is always required, even when no test runner was detected.
		if !*trusted {
			fmt.Fprintln(errOut, runner.ErrUntrusted)
			return 2
		}
		r, err := doctor.Inspect(path)
		if err != nil {
			fmt.Fprintln(errOut, "test:", err)
			return 1
		}
		if len(r.TestCommands) > 0 {
			t := r.TestCommands[0]
			fmt.Fprintf(out, "Running %s in %s (trusted workspace)\n", strings.Join(append([]string{t.Tool}, t.Args...), " "), r.Root)
		}
		if err := runner.Run(context.Background(), r, true, out, errOut, *timeout); err != nil {
			fmt.Fprintln(errOut, "test:", err)
			return 1
		}
		return 0
	default:
		fmt.Fprintln(errOut, "unknown command:", args[0])
		usage(errOut)
		return 2
	}
}

func workspaceArg(args []string, errOut io.Writer) (string, bool) {
	if len(args) > 1 {
		fmt.Fprintln(errOut, "expected at most one workspace path (put flags before the path)")
		return "", false
	}
	if len(args) == 0 {
		return ".", true
	}
	return args[0], true
}

func display(out io.Writer, r doctor.Report) {
	fmt.Fprintln(out, "DevPilot doctor")
	fmt.Fprintln(out, "Workspace:", r.Root)
	fmt.Fprintln(out, "Languages:", summarize(r.Languages))
	fmt.Fprintln(out, "Frameworks:", summarize(r.Frameworks))
	fmt.Fprintln(out, "Package managers:", summarize(r.PackageManagers))
	fmt.Fprintln(out, "Git:", r.Git, "| Docker Compose:", r.DockerCompose)
	for _, t := range r.TestCommands {
		fmt.Fprintf(out, "Test: %s (detected in %s)\n", strings.Join(append([]string{t.Tool}, t.Args...), " "), t.Source)
	}
	for _, f := range r.Findings {
		fmt.Fprintf(out, "[%s] %s: %s\n  Next: %s\n", strings.ToUpper(f.Severity), f.Code, f.Evidence, f.Remedy)
	}
	if len(r.Findings) == 0 {
		fmt.Fprintln(out, "No findings from the supported checks.")
	}
	fmt.Fprintln(out, "Static inspection only; tests are never run by doctor.")
}
func summarize(values []string) string {
	if len(values) == 0 {
		return "not detected"
	}
	return strings.Join(values, ", ")
}
func usage(out io.Writer) {
	fmt.Fprintln(out, "DevPilot — read-only project diagnosis and explicitly trusted test execution")
	fmt.Fprintln(out, "Usage:")
	fmt.Fprintln(out, "  devpilot doctor [--json] [workspace]")
	fmt.Fprintln(out, "  devpilot test --trust [--timeout=90s] [workspace]")
	fmt.Fprintln(out, "Run doctor first; only use test --trust for repositories you trust.")
}
