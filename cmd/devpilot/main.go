package main

import (
	"context"
	"encoding/json"
	"errors"
	"flag"
	"fmt"
	"io"
	"os"
	"os/exec"
	"strings"
	"time"

	"github.com/batuhansimsar/DEVPILOT/internal/doctor"
)

func usage(w io.Writer) {
	fmt.Fprintln(w, "DevPilot — local developer project diagnostics")
	fmt.Fprintln(w, "Usage: devpilot doctor [--json] [path]")
	fmt.Fprintln(w, "       devpilot test --trust [--timeout=2m] [path]")
	fmt.Fprintln(w, "Doctor only reads supported project metadata; test requires explicit trust.")
}

func run(ctx context.Context, args []string, stdout, stderr io.Writer) int {
	if len(args) == 0 || args[0] == "help" || args[0] == "--help" {
		usage(stdout)
		return 0
	}
	switch args[0] {
	case "doctor":
		flags := flag.NewFlagSet("doctor", flag.ContinueOnError)
		flags.SetOutput(stderr)
		jsonOut := flags.Bool("json", false, "machine-readable JSON report")
		if err := flags.Parse(args[1:]); err != nil {
			return 2
		}
		if flags.NArg() > 1 {
			fmt.Fprintln(stderr, "doctor accepts at most one path")
			return 2
		}
		path := "."
		if flags.NArg() == 1 {
			path = flags.Arg(0)
		}
		report, err := doctor.Inspect(path)
		if err != nil {
			fmt.Fprintln(stderr, "doctor:", err)
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
			fmt.Fprintf(stdout, "DevPilot doctor: %s\n", report.Path)
			fmt.Fprintf(stdout, "Languages: %s\n", strings.Join(report.Languages, ", "))
			if len(report.Frameworks) > 0 {
				fmt.Fprintf(stdout, "Frameworks: %s\n", strings.Join(report.Frameworks, ", "))
			}
			if report.PackageManager != "" {
				fmt.Fprintf(stdout, "Package manager: %s\n", report.PackageManager)
			}
			for _, f := range report.Findings {
				fmt.Fprintf(stdout, "[%s] %s\n", strings.ToUpper(f.Level), f.Message)
				if f.Remedy != "" {
					fmt.Fprintf(stdout, "       Next: %s\n", f.Remedy)
				}
			}
		}
		if report.HasWarnings() {
			return 1
		}
		return 0
	case "test":
		flags := flag.NewFlagSet("test", flag.ContinueOnError)
		flags.SetOutput(stderr)
		trust := flags.Bool("trust", false, "explicitly allow execution of project test code")
		timeout := flags.Duration("timeout", 2*time.Minute, "test timeout (maximum 10 minutes)")
		if err := flags.Parse(args[1:]); err != nil {
			return 2
		}
		if flags.NArg() > 1 {
			fmt.Fprintln(stderr, "test accepts at most one path")
			return 2
		}
		if !*trust {
			fmt.Fprintln(stderr, "Refusing to execute untrusted project code. Pass --trust only for repositories you trust.")
			return 2
		}
		if *timeout <= 0 || *timeout > 10*time.Minute {
			fmt.Fprintln(stderr, "timeout must be between 1ns and 10m")
			return 2
		}
		path := "."
		if flags.NArg() == 1 {
			path = flags.Arg(0)
		}
		report, err := doctor.Inspect(path)
		if err != nil {
			fmt.Fprintln(stderr, err)
			return 2
		}
		if report.Tests == nil {
			fmt.Fprintln(stderr, "No supported test command discovered.")
			return 2
		}
		if _, err = exec.LookPath(report.Tests.Executable); err != nil {
			fmt.Fprintln(stderr, "Test executable not installed:", report.Tests.Executable)
			return 2
		}
		cctx, cancel := context.WithTimeout(ctx, *timeout)
		defer cancel()
		cmd := newTrustedTestCommand(cctx, report.Path, report.Tests.Executable, report.Tests.Arguments...)
		cmd.Stdout = stdout
		cmd.Stderr = stderr
		fmt.Fprintf(stderr, "Running trusted project tests: %s %s\n", report.Tests.Executable, strings.Join(report.Tests.Arguments, " "))
		if err := cmd.Run(); err != nil {
			if errors.Is(cctx.Err(), context.DeadlineExceeded) {
				fmt.Fprintln(stderr, "Test timed out.")
			} else {
				fmt.Fprintln(stderr, "Test failed:", err)
			}
			return 1
		}
		return 0
	default:
		fmt.Fprintf(stderr, "Unknown command: %s\n", args[0])
		usage(stderr)
		return 2
	}
}

func main() { os.Exit(run(context.Background(), os.Args[1:], os.Stdout, os.Stderr)) }
