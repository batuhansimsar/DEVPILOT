package main

import "strconv"

// quoteTerminalPath makes untrusted filesystem paths and path-bearing errors
// safe to display in a terminal. Escape sequences, line breaks, and bidi
// formatting characters must never be emitted literally.
func quoteTerminalPath(value string) string {
	return strconv.QuoteToASCII(value)
}
