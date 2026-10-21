package main

import (
	"strconv"
	"strings"
	"testing"
)

func TestQuoteTerminalPath(t *testing.T) {
	for _, value := range []string{
		"src/Dockerfile.prod",
		"evil\x1b[2J\nname.yml",
		"dir/\u202esecret.yml",
		"path/\xffinvalid",
	} {
		t.Run(strconv.QuoteToASCII(value), func(t *testing.T) {
			got := quoteTerminalPath(value)
			if got != strconv.QuoteToASCII(value) || strings.ContainsRune(got, '\x1b') || strings.ContainsRune(got, '\n') || strings.ContainsRune(got, '\u202e') {
				t.Fatalf("unsafe terminal path: %q", got)
			}
			decoded, err := strconv.Unquote(got)
			if err != nil || decoded != value {
				t.Fatalf("path not preserved: decoded=%q err=%v", decoded, err)
			}
		})
	}
}
