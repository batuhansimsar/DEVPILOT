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
	".wgsl":    "WGSL",
	".glsl":    "GLSL",
	".vert":    "GLSL",
	".frag":    "GLSL",
	// GLSL stage-specific files are source files, not binary SPIR-V assets.
	".comp":  "GLSL",
	".geom":  "GLSL",
	".tesc":  "GLSL",
	".tese":  "GLSL",
	".vsh":   "GLSL",
	".fsh":   "GLSL",
	".hlsl":  "HLSL",
	".metal": "Metal Shading Language",
	// HDL design and verification sources. The .v suffix is deliberately
	// excluded because it is shared by Verilog and the V language.
	".vhd":    "VHDL",
	".vhdl":   "VHDL",
	".sv":     "SystemVerilog",
	".svh":    "SystemVerilog",
	".astro":  "Astro",
	".prisma": "Prisma Schema",
	".mdx":    "MDX",
	// Infrastructure-as-code and declarative configuration sources.
	".tofu":       "OpenTofu",
	".tfvars":     "Terraform",
	".bicep":      "Bicep",
	".bicepparam": "Bicep",
	".cue":        "CUE",

	// WebAssembly text modules, test scripts, and component interface types.
	".wat":  "WebAssembly Text",
	".wast": "WebAssembly Text",
	".wit":  "WebAssembly Interface Types",
}

func supplementalSourceLanguage(name string) (string, bool) {
	lower := strings.ToLower(name)
	// Terraform and OpenTofu also support JSON configuration syntax. Using
	// filepath.Ext alone would classify both as generic .json files.
	switch {
	case strings.HasSuffix(lower, ".tf.json"), strings.HasSuffix(lower, ".tfvars.json"):
		return "Terraform", true
	case strings.HasSuffix(lower, ".tofu.json"):
		return "OpenTofu", true
	}
	language, ok := supplementalSourceLanguages[filepath.Ext(lower)]
	return language, ok
}
