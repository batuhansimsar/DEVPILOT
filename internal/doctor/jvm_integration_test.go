package doctor

import (
	"strings"
	"testing"
)

func TestInspectJVMTestDiscovery(t *testing.T) {
	for _, tc := range []struct {
		name, manifest, executable string
	}{
		{"Maven", "pom.xml", "mvn"},
		{"Gradle", "build.gradle", "gradle"},
		{"Gradle Kotlin DSL", "build.gradle.kts", "gradle"},
	} {
		t.Run(tc.name, func(t *testing.T) {
			root := t.TempDir()
			write(t, root, tc.manifest, "project marker")
			r, err := Inspect(root)
			if err != nil {
				t.Fatal(err)
			}
			if len(r.Languages) != 1 || r.Languages[0] != "Java/Kotlin" {
				t.Fatalf("languages = %v", r.Languages)
			}
			if r.Tests == nil || r.Tests.Executable != tc.executable || strings.Join(r.Tests.Arguments, " ") != "test" {
				t.Fatalf("wrong JVM test command: %+v", r.Tests)
			}
			if !finding(r, "test-discovered") {
				t.Fatalf("missing test discovery finding: %+v", r.Findings)
			}
		})
	}
}

func TestInspectJVMConflictDoesNotGuessTestRunner(t *testing.T) {
	root := t.TempDir()
	write(t, root, "pom.xml", "project marker")
	write(t, root, "build.gradle", "project marker")
	r, err := Inspect(root)
	if err != nil {
		t.Fatal(err)
	}
	if !finding(r, "jvm-build-conflict") || r.Tests != nil {
		t.Fatalf("conflicting build systems must not auto-select tests: %+v", r)
	}
}

func TestInspectJVMPreservesExistingGoTestCommand(t *testing.T) {
	root := t.TempDir()
	write(t, root, "go.mod", "module example.com/x\ngo 1.23\n")
	write(t, root, "pom.xml", "project marker")
	r, err := Inspect(root)
	if err != nil {
		t.Fatal(err)
	}
	if r.Tests == nil || r.Tests.Executable != "go" || strings.Join(r.Tests.Arguments, " ") != "test ./..." {
		t.Fatalf("existing Go test command replaced: %+v", r.Tests)
	}
}
