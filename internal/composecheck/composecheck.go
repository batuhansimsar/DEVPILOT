// Package composecheck performs local-only Docker setup diagnostics without
// contacting the Docker daemon or executing project-controlled commands.
package composecheck

import (
	"os"
	"path/filepath"
	"sort"
	"strings"
)

// Finding explains an observation from root-level, regular Docker files.
type Finding struct {
	Level   string
	Code    string
	Message string
	Remedy  string
}

// Inspect checks the common Compose configuration names, Dockerfile, and
// .dockerignore. The dependency injection enables deterministic tests. No file
// contents are parsed and symlinked files are never considered evidence.
func Inspect(root string, lookPath func(string) (string, error)) []Finding {
	regular := func(name string) bool {
		info, err := os.Lstat(filepath.Join(root, name))
		return err == nil && info.Mode().IsRegular()
	}
	composeFiles := []string{}
	for _, name := range []string{"compose.yaml", "compose.yml", "docker-compose.yml", "docker-compose.yaml"} {
		if regular(name) {
			composeFiles = append(composeFiles, name)
		}
	}
	dockerfile := regular("Dockerfile")
	if len(composeFiles) == 0 && !dockerfile {
		return nil
	}
	out := []Finding{}
	add := func(level, code, message, remedy string) { out = append(out, Finding{level, code, message, remedy}) }
	if len(composeFiles) > 0 {
		sort.Strings(composeFiles)
		add("info", "docker-compose-found", "Docker Compose configuration file(s): "+strings.Join(composeFiles, ", "), "Review service definitions with docker compose config in a trusted workspace; DevPilot did not parse or execute the configuration.")
	}
	if len(composeFiles) > 1 {
		add("warning", "docker-compose-multiple-files", "Multiple default Docker Compose filenames found: "+strings.Join(composeFiles, ", "), "Confirm which Compose file is intended; specify -f explicitly or remove obsolete files.")
	}
	if _, err := lookPath("docker"); err != nil {
		add("warning", "docker-cli-missing", "Docker configuration detected but the docker command is not on PATH", "Install Docker CLI if this project needs container services; daemon availability was not checked.")
	} else {
		add("pass", "docker-cli-found", "Docker CLI executable is on PATH (daemon not checked)", "")
	}
	if dockerfile && !regular(".dockerignore") {
		add("info", "dockerignore-not-found", "Dockerfile found without a root .dockerignore", "Consider excluding local secrets, Git metadata and build outputs from the Docker build context.")
	}
	return out
}
