package doctor

import (
	"context"
	"fmt"
	"os"
	"os/exec"
	"regexp"
	"strconv"
	"strings"
	"time"
)

type goVersion struct{ major, minor, patch int }

var installedGoPattern = regexp.MustCompile(`\bgo([0-9]+)\.([0-9]+)(?:\.([0-9]+))?(?:\s|$)`)

func parseGoVersion(value string) (goVersion, bool) {
	parts := strings.Split(value, ".")
	if len(parts) != 2 && len(parts) != 3 {
		return goVersion{}, false
	}
	numbers := [3]int{}
	for i, p := range parts {
		if p == "" {
			return goVersion{}, false
		}
		for _, c := range p {
			if c < '0' || c > '9' {
				return goVersion{}, false
			}
		}
		n, err := strconv.Atoi(p)
		if err != nil || n < 0 {
			return goVersion{}, false
		}
		numbers[i] = n
	}
	return goVersion{numbers[0], numbers[1], numbers[2]}, true
}

func (v goVersion) lessThan(other goVersion) bool {
	if v.major != other.major {
		return v.major < other.major
	}
	if v.minor != other.minor {
		return v.minor < other.minor
	}
	return v.patch < other.patch
}

func (v goVersion) String() string {
	if v.patch == 0 {
		return fmt.Sprintf("%d.%d", v.major, v.minor)
	}
	return fmt.Sprintf("%d.%d.%d", v.major, v.minor, v.patch)
}

func requiredGoVersion(data []byte) (goVersion, bool) {
	for _, line := range strings.Split(string(data), "\n") {
		parts := strings.Fields(strings.SplitN(line, "//", 2)[0])
		if len(parts) == 2 && parts[0] == "go" {
			return parseGoVersion(parts[1])
		}
	}
	return goVersion{}, false
}

func runningGoVersion(output string) (goVersion, bool) {
	matches := installedGoPattern.FindStringSubmatch(output)
	if matches == nil {
		return goVersion{}, false
	}
	version := matches[1] + "." + matches[2]
	if matches[3] != "" {
		version += "." + matches[3]
	}
	return parseGoVersion(version)
}

// inspectGoVersion compares a project's declared minimum Go version to the
// local toolchain. GOTOOLCHAIN=local prevents implicit downloads or switching.
// This executes only the installed `go version` executable, never project code.
func inspectGoVersion(root string, add func(level, code, message, remedy string)) {
	data, found, err := readMarker(root, "go.mod")
	if err != nil {
		add("warning", "go-mod-unreadable", "Cannot read go.mod to check Go version", "Check that go.mod is a regular file under 1 MiB.")
		return
	}
	if !found {
		return
	}
	required, ok := requiredGoVersion(data)
	if !ok {
		return
	}
	binary, err := exec.LookPath("go")
	if err != nil {
		return
	} // Existing tool check already reports missing Go.
	ctx, cancel := context.WithTimeout(context.Background(), 3*time.Second)
	defer cancel()
	cmd := exec.CommandContext(ctx, binary, "version")
	cmd.Dir = os.TempDir()
	cmd.Env = append(os.Environ(), "GOTOOLCHAIN=local", "GOWORK=off", "GOENV=off")
	out, err := cmd.Output()
	if err != nil {
		add("info", "go-version-unavailable", "Go toolchain version could not be checked", "Run 'go version' manually to verify the required version.")
		return
	}
	installed, ok := runningGoVersion(string(out))
	if !ok {
		return
	} // Development/prerelease builds may not match stable format.
	if installed.lessThan(required) {
		add("warning", "go-version-too-old", fmt.Sprintf("go.mod requires Go %s but installed Go is %s", required, installed), "Install a compatible Go toolchain before building or testing this project.")
	}
}
