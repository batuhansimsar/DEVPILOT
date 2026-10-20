package main

import (
	"encoding/json"
	"io"
)

// printJSONTestPreview emits a structured test plan without executing anything.
// The arguments remain a JSON array rather than a shell command string.
func printJSONTestPreview(w io.Writer, directory, executable string, arguments []string) error {
	return json.NewEncoder(w).Encode(map[string]any{
		"working_directory": directory,
		"executable":        executable,
		"arguments":         arguments,
		"executed":          false,
	})
}
