package main

import (
	"encoding/json"
	"flag"
	"fmt"
	"io"
	"os"
	"strings"

	"github.com/batuhansimsar/DEVPILOT/internal/projecttree"
)

func run(args []string, stdout, stderr io.Writer) int {
	f := flag.NewFlagSet("tree", flag.ContinueOnError)
	f.SetOutput(stderr)
	depth := f.Int("depth", 2, "maximum directory depth, 0–20")
	limit := f.Int("limit", 500, "maximum entries, 1–10000")
	hidden := f.Bool("hidden", false, "include hidden names (not contents)")
	outputJSON := f.Bool("json", false, "output JSON")
	if err := f.Parse(args); err != nil {
		return 2
	}
	if f.NArg() > 1 {
		fmt.Fprintln(stderr, "expected at most one workspace path")
		return 2
	}
	path := "."
	if f.NArg() == 1 {
		path = f.Arg(0)
	}
	r, err := projecttree.Scan(path, projecttree.Options{MaxDepth: *depth, MaxEntries: *limit, ShowHidden: *hidden})
	if err != nil {
		fmt.Fprintln(stderr, err)
		return 2
	}
	if *outputJSON {
		e := json.NewEncoder(stdout)
		e.SetIndent("", "  ")
		if err := e.Encode(r); err != nil {
			fmt.Fprintln(stderr, err)
			return 2
		}
		return 0
	}
	fmt.Fprintln(stdout, "Project tree:", r.Root)
	for _, entry := range r.Entries {
		name := filepathBase(entry.Path)
		suffix := ""
		if entry.Kind == "directory" {
			suffix = "/"
		} else if entry.Kind == "symlink" {
			suffix = " -> [symlink; not followed]"
		}
		fmt.Fprintf(stdout, "%s%s%s\n", strings.Repeat("  ", entry.Depth), name, suffix)
	}
	if r.Truncated {
		fmt.Fprintln(stdout, "[truncated: entry limit reached]")
	}
	for _, skipped := range r.Skipped {
		fmt.Fprintln(stdout, "[skipped]", skipped)
	}
	return 0
}
func filepathBase(p string) string { parts := strings.Split(p, "/"); return parts[len(parts)-1] }
func main()                        { os.Exit(run(os.Args[1:], os.Stdout, os.Stderr)) }
