package doctor

import (
	"os"
	"path/filepath"
	"sort"
	"strings"
)

// dotnetInventory represents trusted filename metadata only. Project and solution
// contents are not parsed, and no dotnet command is executed during inspection.
type dotnetInventory struct {
	Found      bool
	Languages  []string
	TestTarget string
	Ambiguous  bool
}

func discoverDotnet(root string) (dotnetInventory, error) {
	entries, err := os.ReadDir(root)
	if err != nil {
		return dotnetInventory{}, err
	}

	var projects, solutions []string
	languages := make(map[string]bool)
	for _, entry := range entries {
		// Do not follow directory entries or symlinks (including symlinked manifests).
		if !entry.Type().IsRegular() {
			continue
		}
		name := entry.Name()
		switch strings.ToLower(filepath.Ext(name)) {
		case ".csproj":
			languages["C#"] = true
			projects = append(projects, name)
		case ".fsproj":
			languages["F#"] = true
			projects = append(projects, name)
		case ".vbproj":
			languages["Visual Basic"] = true
			projects = append(projects, name)
		case ".sln", ".slnx", ".slnf":
			solutions = append(solutions, name)
		}
	}

	out := dotnetInventory{Found: len(projects)+len(solutions) > 0}
	for language := range languages {
		out.Languages = append(out.Languages, language)
	}
	sort.Strings(out.Languages)
	sort.Strings(projects)
	sort.Strings(solutions)
	if out.Found && len(out.Languages) == 0 {
		out.Languages = []string{".NET"}
	}
	// Prefer exactly one solution over project files; otherwise only select a
	// project if it is the single project and there are no solutions.
	switch {
	case len(solutions) == 1:
		out.TestTarget = filepath.Join(root, solutions[0])
	case len(solutions) == 0 && len(projects) == 1:
		out.TestTarget = filepath.Join(root, projects[0])
	case out.Found:
		out.Ambiguous = true
	}
	return out, nil
}
