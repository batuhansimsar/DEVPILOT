package main

import (
	"encoding/json"
	"flag"
	"fmt"
	"io"
	"strconv"
	"strings"

	"github.com/batuhansimsar/DEVPILOT/internal/projecttree"
)

func runMap(args []string, stdout, stderr io.Writer) int {
	flags := flag.NewFlagSet("map", flag.ContinueOnError)
	flags.SetOutput(stderr)
	depth := flags.Int("depth", projecttree.DefaultDepth, "maximum directory depth (1 to 8)")
	jsonOut := flags.Bool("json", false, "machine-readable JSON")
	if err := flags.Parse(args); err != nil {
		return 2
	}
	if flags.NArg() > 1 {
		fmt.Fprintln(stderr, "map accepts at most one path")
		return 2
	}
	path := "."
	if flags.NArg() == 1 {
		path = flags.Arg(0)
	}
	result, err := projecttree.MapDirectory(path, *depth)
	if err != nil {
		fmt.Fprintln(stderr, "map:", err)
		return 2
	}
	if *jsonOut {
		encoder := json.NewEncoder(stdout)
		encoder.SetIndent("", "  ")
		if err := encoder.Encode(result); err != nil {
			fmt.Fprintln(stderr, "map:", err)
			return 2
		}
		return 0
	}
	fmt.Fprintf(stdout, "DevPilot map: %s\n", strconv.QuoteToASCII(result.Root))
	for _, entry := range result.Entries {
		fmt.Fprintf(stdout, "%s%s (%s)\n", strings.Repeat("  ", entry.Depth-1), strconv.QuoteToASCII(entry.Path), entry.Type)
	}
	if len(result.SkippedDirectories) > 0 {
		fmt.Fprintf(stdout, "Excluded %d generated/tool directories\n", len(result.SkippedDirectories))
	}
	if result.Truncated {
		fmt.Fprintln(stdout, "WARNING: directory map truncated at safety limit")
	}
	for _, warning := range result.Warnings {
		fmt.Fprintf(stderr, "map warning: %s\n", warning)
	}
	return 0
}
