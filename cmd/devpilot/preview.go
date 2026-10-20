package main

import (
	"fmt"
	"io"
)

// printTestPreview shows process argument boundaries without running a command.
// Quoting prevents control characters in untrusted filenames from changing
// the terminal display or making arguments resemble shell syntax.
func printTestPreview(w io.Writer, directory, executable string, arguments []string) {
	fmt.Fprintln(w, "Dry run: no command executed.")
	fmt.Fprintf(w, "Working directory: %q\nExecutable: %q\n", directory, executable)
	fmt.Fprintln(w, "Arguments:")
	for _, arg := range arguments {
		fmt.Fprintf(w, "  %q\n", arg)
	}
}
