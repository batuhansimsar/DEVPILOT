package analyze

import (
	"path/filepath"
	"strings"
)

// supplementalSourceLanguages recognizes nontraditional source formats
// without opening or parsing untrusted project files.
var supplementalSourceLanguages = map[string]string{
	".ipynb":   "Jupyter Notebook",
	".proto":   "Protocol Buffers",
	".graphql": "GraphQL",
	".gql":     "GraphQL",
	".sol":     "Solidity",
	".nix":     "Nix",
}

func supplementalSourceLanguage(name string) (string, bool) {
	language, ok := supplementalSourceLanguages[strings.ToLower(filepath.Ext(name))]
	return language, ok
}
