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
    "sort"
    "strings"
    "time"

    "github.com/batuhansimsar/DEVPILOT/internal/doctor"
)

func main() { os.Exit(run(os.Args[1:], os.Stdout, os.Stderr)) }

func run(args []string, stdout, stderr io.Writer) int {
    if len(args) == 0 { args = []string{"doctor"} }
    switch args[0] {
    case "doctor":
        fs := flag.NewFlagSet("doctor", flag.ContinueOnError)
        fs.SetOutput(stderr)
        jsonFlag := fs.Bool("json", false, "print machine-readable JSON")
        if err := fs.Parse(args[1:]); err != nil { return 2 }
        if fs.NArg() > 1 { fmt.Fprintln(stderr, "doctor accepts at most one directory"); return 2 }
        path := "."
        if fs.NArg() == 1 { path = fs.Arg(0) }
        report, err := doctor.Inspect(context.Background(), path)
        if err != nil { fmt.Fprintln(stderr, "devpilot doctor:", err); return 1 }
        if *jsonFlag {
            encoder := json.NewEncoder(stdout)
            encoder.SetIndent("", "  ")
            if err := encoder.Encode(report); err != nil { fmt.Fprintln(stderr, err); return 1 }
        } else { display(stdout, report) }
        return 0
    case "test":
        fs := flag.NewFlagSet("test", flag.ContinueOnError)
        fs.SetOutput(stderr)
        trust := fs.Bool("trust", false, "explicitly authorize execution of project-owned test commands")
        runner := fs.String("runner", "", "test runner (go, node, python, rust, dotnet)")
        timeout := fs.Duration("timeout", 2*time.Minute, "maximum test duration")
        if err := fs.Parse(args[1:]); err != nil { return 2 }
        if fs.NArg() > 1 { fmt.Fprintln(stderr, "test accepts at most one directory"); return 2 }
        if !*trust { fmt.Fprintln(stderr, "refusing to execute repository code: add --trust after reviewing the project and its test scripts"); return 2 }
        if *timeout < time.Second || *timeout > 30*time.Minute { fmt.Fprintln(stderr, "timeout must be between 1 second and 30 minutes"); return 2 }
        path := "."
        if fs.NArg() == 1 { path = fs.Arg(0) }
        report, err := doctor.Inspect(context.Background(), path)
        if err != nil { fmt.Fprintln(stderr, err); return 1 }
        if len(report.TestCommands) == 0 { fmt.Fprintln(stderr, "no supported test command detected"); return 2 }
        selected := *runner
        if selected == "" {
            if len(report.TestCommands) != 1 { fmt.Fprintln(stderr, "multiple test runners detected; select one with --runner"); return 2 }
            for k := range report.TestCommands { selected = k }
        }
        argv, ok := report.TestCommands[selected]
        if !ok { fmt.Fprintf(stderr, "runner %q not detected in workspace\n", selected); return 2 }
        if selected == "node" && len(report.PackageManagers) != 1 { fmt.Fprintln(stderr, "conflicting Node lockfiles; choose one package manager before running tests"); return 2 }
        if _, err := exec.LookPath(argv[0]); err != nil { fmt.Fprintf(stderr, "%s executable not found in PATH\n", argv[0]); return 2 }
        fmt.Fprintf(stdout, "Running in trusted workspace %s: %s\n", report.Root, strings.Join(argv, " "))
        ctx, cancel := context.WithTimeout(context.Background(), *timeout)
        defer cancel()
        cmd := exec.CommandContext(ctx, argv[0], argv[1:]...)
        cmd.Dir = report.Root
        cmd.Stdin = os.Stdin
        cmd.Stdout, cmd.Stderr = stdout, stderr
        if err := cmd.Run(); err != nil {
            if errors.Is(ctx.Err(), context.DeadlineExceeded) { fmt.Fprintln(stderr, "test command timed out"); return 124 }
            var exitErr *exec.ExitError
            if errors.As(err, &exitErr) { return exitErr.ExitCode() }
            fmt.Fprintln(stderr, "could not run tests:", err)
            return 1
        }
        return 0
    case "help", "--help", "-h":
        fmt.Fprintln(stdout, "DevPilot - local developer project diagnostics\n\nUsage:\n  devpilot doctor [--json] [directory]\n  devpilot test --trust [--runner go|node|python|rust|dotnet] [--timeout 2m] [directory]\n\nDoctor is read-only. Test runs project-owned code only with explicit --trust.")
        return 0
    default:
        fmt.Fprintf(stderr, "unknown command %q; try devpilot help\n", args[0]); return 2
    }
}

func display(out io.Writer, report doctor.Report) {
    fmt.Fprintln(out, "DevPilot Doctor")
    fmt.Fprintln(out, "Workspace:", report.Root)
    fmt.Fprintln(out, "Languages:", items(report.Languages))
    fmt.Fprintln(out, "Frameworks:", items(report.Frameworks))
    fmt.Fprintln(out, "Package managers:", items(report.PackageManagers))
    fmt.Fprintln(out, "\nFindings:")
    for _, f := range report.Findings {
        fmt.Fprintf(out, "  [%s] %s: %s\n", strings.ToUpper(f.Severity), f.Code, f.Message)
        if f.Evidence != "" { fmt.Fprintf(out, "    Evidence: %s\n", f.Evidence) }
        if f.Remedy != "" { fmt.Fprintf(out, "    Next: %s\n", f.Remedy) }
    }
    if len(report.TestCommands) > 0 {
        fmt.Fprintln(out, "\nDiscovered tests (not executed):")
        names := make([]string, 0, len(report.TestCommands))
        for name := range report.TestCommands { names = append(names, name) }
        sort.Strings(names)
        for _, name := range names { fmt.Fprintf(out, "  %s: %s\n", name, strings.Join(report.TestCommands[name], " ")) }
        fmt.Fprintln(out, "Run tests only after reviewing the repo: devpilot test --trust")
    }
}

func items(values []string) string {
    if len(values) == 0 { return "not detected" }
    return strings.Join(values, ", ")
}
