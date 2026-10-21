package main

import (
	"context"
	"encoding/json"
	"errors"
	"flag"
	"fmt"
	"io"
	"net"
	"os"
	"os/exec"
	"strconv"
	"strings"
	"time"

	"github.com/batuhansimsar/DEVPILOT/internal/dockercheck"
	"github.com/batuhansimsar/DEVPILOT/internal/doctor"
	"github.com/batuhansimsar/DEVPILOT/internal/portcheck"
)

func usage(w io.Writer) {
	fmt.Fprintln(w, "DevPilot — local developer project diagnostics")
	fmt.Fprintln(w, "Usage: devpilot doctor [--json] [path]")
	fmt.Fprintln(w, "       devpilot dockerfile [--json] [path]")
	fmt.Fprintln(w, "       devpilot analyze [--json] [path]")
	fmt.Fprintln(w, "       devpilot test [--dry-run [--json] | --trust] [--timeout=2m] [path]")
	fmt.Fprintln(w, "       devpilot docker [--json] [ps]")
	fmt.Fprintln(w, "       devpilot check [--json] [--timeout=3s] host port")
	fmt.Fprintln(w, "Doctor only reads supported project metadata; test requires explicit trust.")
	fmt.Fprintln(w, "Docker queries are read-only and have a 5-second timeout.")
}

func run(ctx context.Context, args []string, stdout, stderr io.Writer) int {
	if len(args) == 0 || args[0] == "help" || args[0] == "--help" {
		usage(stdout)
		return 0
	}
	switch args[0] {
	case "analyze":
		return analyzeCommand(args[1:], stdout, stderr)
	case "dockerfile":
		return dockerfileCommand(args[1:], stdout, stderr)
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
			fmt.Fprintln(stderr, "doctor:", escapeTerminalText(err.Error()))
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
			fmt.Fprintf(stdout, "DevPilot doctor: %s\n", quoteTerminalPath(report.Path))
			fmt.Fprintf(stdout, "Languages: %s\n", strings.Join(report.Languages, ", "))
			if len(report.Frameworks) > 0 {
				fmt.Fprintf(stdout, "Frameworks: %s\n", strings.Join(report.Frameworks, ", "))
			}
			if report.PackageManager != "" {
				fmt.Fprintf(stdout, "Package manager: %s\n", report.PackageManager)
			}
			for _, f := range report.Findings {
				fmt.Fprintf(stdout, "[%s] %s\n", strings.ToUpper(f.Level), escapeTerminalText(f.Message))
				if f.Remedy != "" {
					fmt.Fprintf(stdout, "       Next: %s\n", escapeTerminalText(f.Remedy))
				}
			}
		}
		if report.HasWarnings() {
			return 1
		}
		return 0
	case "check":
		flags := flag.NewFlagSet("check", flag.ContinueOnError)
		flags.SetOutput(stderr)
		jsonOut := flags.Bool("json", false, "machine-readable connectivity result")
		timeout := flags.Duration("timeout", 3*time.Second, "TCP connection timeout (100ms to 30s)")
		if err := flags.Parse(args[1:]); err != nil {
			return 2
		}
		if flags.NArg() != 2 {
			fmt.Fprintln(stderr, "check requires a host and port")
			return 2
		}
		port, err := strconv.Atoi(flags.Arg(1))
		if err != nil {
			fmt.Fprintln(stderr, "port must be an integer between 1 and 65535")
			return 2
		}
		result, err := portcheck.Check(ctx, flags.Arg(0), port, *timeout)
		if err != nil {
			fmt.Fprintln(stderr, "check:", err)
			return 2
		}
		if *jsonOut {
			enc := json.NewEncoder(stdout)
			enc.SetIndent("", "  ")
			if err := enc.Encode(result); err != nil {
				fmt.Fprintln(stderr, err)
				return 2
			}
		} else {
			status := "unreachable"
			if result.Reachable {
				status = "reachable"
			}
			fmt.Fprintf(stdout, "%s — %s (%.1f ms)\n", net.JoinHostPort(result.Host, strconv.Itoa(result.Port)), status, result.LatencyMS)
			if result.Error != "" {
				fmt.Fprintln(stderr, result.Error)
			}
		}
		if result.Reachable {
			return 0
		}
		return 1
	case "test":
		flags := flag.NewFlagSet("test", flag.ContinueOnError)
		flags.SetOutput(stderr)
		trust := flags.Bool("trust", false, "explicitly allow execution of project test code")
		dryRun := flags.Bool("dry-run", false, "preview test command without executing it")
		jsonOut := flags.Bool("json", false, "emit a machine-readable test preview (requires --dry-run)")
		timeout := flags.Duration("timeout", 2*time.Minute, "test timeout (maximum 10 minutes)")
		if err := flags.Parse(args[1:]); err != nil {
			return 2
		}
		if flags.NArg() > 1 {
			fmt.Fprintln(stderr, "test accepts at most one path")
			return 2
		}
		if *dryRun && *trust {
			fmt.Fprintln(stderr, "--dry-run and --trust cannot be combined")
			return 2
		}
		if *jsonOut && !*dryRun {
			fmt.Fprintln(stderr, "--json requires --dry-run for the test command")
			return 2
		}
		if !*trust && !*dryRun {
			fmt.Fprintln(stderr, "Refusing to execute untrusted project code. Pass --trust to execute or --dry-run to preview.")
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
			fmt.Fprintln(stderr, escapeTerminalText(err.Error()))
			return 2
		}
		if report.Tests == nil {
			fmt.Fprintln(stderr, "No supported test command discovered.")
			return 2
		}
		if *dryRun {
			if *jsonOut {
				if err := printJSONTestPreview(stdout, report.Path, report.Tests.Executable, report.Tests.Arguments); err != nil {
					fmt.Fprintln(stderr, "Cannot write test plan:", err)
					return 2
				}
			} else {
				printTestPreview(stdout, report.Path, report.Tests.Executable, report.Tests.Arguments)
			}
			return 0
		}
		if _, err = exec.LookPath(report.Tests.Executable); err != nil {
			fmt.Fprintln(stderr, "Test executable not installed:", report.Tests.Executable)
			return 2
		}
		cctx, cancel := context.WithTimeout(ctx, *timeout)
		defer cancel()
		cmd := exec.CommandContext(cctx, report.Tests.Executable, report.Tests.Arguments...)
		cmd.Dir = report.Path
		cmd.Stdout = stdout
		cmd.Stderr = stderr
		fmt.Fprintf(stderr, "Running trusted project tests: %s %s\n", report.Tests.Executable, escapeTerminalText(strings.Join(report.Tests.Arguments, " ")))
		if err := cmd.Run(); err != nil {
			if errors.Is(cctx.Err(), context.DeadlineExceeded) {
				fmt.Fprintln(stderr, "Test timed out.")
			} else {
				fmt.Fprintln(stderr, "Test failed:", err)
			}
			return 1
		}
		return 0
	case "docker":
		flags := flag.NewFlagSet("docker", flag.ContinueOnError)
		flags.SetOutput(stderr)
		jsonOut := flags.Bool("json", false, "machine-readable JSON report")
		if err := flags.Parse(args[1:]); err != nil {
			return 2
		}
		if flags.NArg() > 1 || (flags.NArg() == 1 && flags.Arg(0) != "ps") {
			fmt.Fprintln(stderr, "docker accepts only the optional ps subcommand")
			return 2
		}
		enc := json.NewEncoder(stdout)
		enc.SetIndent("", "  ")
		if flags.NArg() == 1 {
			report := dockercheck.List(ctx, nil)
			if *jsonOut {
				if err := enc.Encode(report); err != nil {
					fmt.Fprintln(stderr, err)
					return 2
				}
			} else if report.Available {
				fmt.Fprintf(stdout, "Running containers: %d\n", len(report.Items))
				for _, item := range report.Items {
					fmt.Fprintln(stdout, string(item))
				}
			} else {
				fmt.Fprintln(stderr, report.Detail)
			}
			if !report.Available {
				return 1
			}
			return 0
		}
		report := dockercheck.Inspect(ctx, nil)
		if *jsonOut {
			if err := enc.Encode(report); err != nil {
				fmt.Fprintln(stderr, err)
				return 2
			}
		} else {
			fmt.Fprintf(stdout, "Docker installed: %t\nDocker daemon reachable: %t\n", report.Installed, report.Reachable)
			if report.Version != "" {
				fmt.Fprintf(stdout, "Server version: %s\n", report.Version)
			}
			if report.Detail != "" {
				fmt.Fprintln(stderr, report.Detail)
			}
		}
		if !report.Reachable {
			return 1
		}
		return 0
	default:
		fmt.Fprintf(stderr, "Unknown command: %s\n", escapeTerminalText(args[0]))
		usage(stderr)
		return 2
	}
}

func main() { os.Exit(run(context.Background(), os.Args[1:], os.Stdout, os.Stderr)) }

// escapeTerminalText prevents control characters from untrusted workspace paths
// and diagnostic messages from altering the terminal display. Quotes are not
// added around ordinary prose; JSON output retains the original values.
func escapeTerminalText(value string) string {
	quoted := strconv.QuoteToASCII(value)
	return quoted[1 : len(quoted)-1]
}
