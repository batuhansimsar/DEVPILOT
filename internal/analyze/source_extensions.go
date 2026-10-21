package analyze

// extendedLanguage identifies source extensions omitted from the core language
// inventory. Only unambiguous extensions are included: for example, .h and .m
// may belong to more than one language and should not be guessed from a suffix.
// Inspect passes a lowercase extension here, avoiding platform-specific casing.
func extendedLanguage(extension string) (string, bool) {
	switch extension {
	case ".hh", ".hpp", ".hxx", ".cxx", ".c++", ".ixx", ".cppm":
		return "C++", true
	case ".kts":
		return "Kotlin", true
	case ".csx":
		return "C#", true
	case ".tfvars":
		return "Terraform", true
	case ".proto":
		return "Protocol Buffers", true
	case ".graphql", ".gql":
		return "GraphQL", true
	case ".prisma":
		return "Prisma", true
	case ".nix":
		return "Nix", true
	case ".cue":
		return "CUE", true
	case ".mm":
		return "Objective-C++", true
	case ".pyi", ".pyw":
		return "Python", true
	case ".pyx", ".pxd", ".pxi":
		return "Cython", true
	case ".ps1", ".psm1", ".psd1":
		return "PowerShell", true
	case ".gd":
		return "GDScript", true
	case ".nim":
		return "Nim", true
	case ".ml", ".mli":
		return "OCaml", true
	case ".typ":
		return "Typst", true
	default:
		return "", false
	}
}
