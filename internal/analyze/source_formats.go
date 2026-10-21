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
	".comp":    "GLSL",
	".geom":    "GLSL",
	".tesc":    "GLSL",
	".tese":    "GLSL",
	".vsh":     "GLSL",
	".fsh":     "GLSL",
	".hlsl":    "HLSL",
	".metal":   "Metal Shading Language",
	// HDL design and verification sources. The .v suffix is deliberately
	// excluded because it is shared by Verilog and the V language.
	".vhd":    "VHDL",
	".vhdl":   "VHDL",
	".sv":     "SystemVerilog",
	".svh":    "SystemVerilog",
	".astro":   "Astro",
	".prisma":  "Prisma Schema",
	".mdx":     "MDX",
}

func supplementalSourceLanguage(name string) (string, bool) {
	language, ok := supplementalSourceLanguages[strings.ToLower(filepath.Ext(name))]
	return language, ok
}
