package analyze

import (
	"os"
	"path/filepath"
	"reflect"
	"runtime"
	"sort"
	"testing"
)

func TestAdditionalDotnetManifestNames(t *testing.T) {
	for _, tc := range []struct {
		name string
		want bool
	}{
		{"Filtered.slnf", true},
		{"FILTERED.SLNF", true},
		{"Directory.Packages.props", true},
		{"Directory.Build.props", true},
		{"Directory.Build.targets", true},
		{"global.json", true},
		{"NuGet.Config", true},
		{"nuget.config", true},
		{"packages.lock.json", true},
		{"Directory.Packages.props.bak", false},
		{"Directory.Build.targets.disabled", false},
		{"Filtered.slnf.bak", false},
		{"Other.props", false},
		{"Other.targets", false},
		{"directory.packages.props", false},
		{"global.json.old", false},
	} {
		t.Run(tc.name, func(t *testing.T) {
			if got := isDotnetManifest(tc.name); got != tc.want {
				t.Errorf("isDotnetManifest(%q) = %t, want %t", tc.name, got, tc.want)
			}
		})
	}
}

func TestInspectDotnetBuildAndRestoreMetadata(t *testing.T) {
	root := t.TempDir()
	valid := []string{
		"Filtered.slnf",
		"Directory.Packages.props",
		"Directory.Build.props",
		"Directory.Build.targets",
		"global.json",
		"NuGet.Config",
		"src/packages.lock.json",
	}
	for _, name := range append(append([]string{}, valid...), "Directory.Packages.props.bak", "Other.props") {
		path := filepath.Join(root, filepath.FromSlash(name))
		if err := os.MkdirAll(filepath.Dir(path), 0700); err != nil {
			t.Fatal(err)
		}
		if err := os.WriteFile(path, nil, 0600); err != nil {
			t.Fatal(err)
		}
	}
	report, err := Inspect(root)
	if err != nil {
		t.Fatal(err)
	}
	want := make([]string, 0, len(valid))
	for _, name := range valid {
		want = append(want, name+" (.NET)")
	}
	sort.Strings(want)
	if !reflect.DeepEqual(report.Manifests, want) {
		t.Fatalf("Manifests = %q, want %q", report.Manifests, want)
	}
	if report.FileCount != len(valid)+2 {
		t.Fatalf("FileCount = %d, want %d", report.FileCount, len(valid)+2)
	}
}

func TestInspectSkipsSymlinkedDotnetMetadata(t *testing.T) {
	if runtime.GOOS == "windows" {
		t.Skip("symlinks may require privileges on Windows")
	}
	root := t.TempDir()
	external := filepath.Join(t.TempDir(), "Directory.Packages.props")
	if err := os.WriteFile(external, []byte("private"), 0600); err != nil {
		t.Fatal(err)
	}
	if err := os.Symlink(external, filepath.Join(root, "Directory.Packages.props")); err != nil {
		t.Fatal(err)
	}
	report, err := Inspect(root)
	if err != nil {
		t.Fatal(err)
	}
	if report.FileCount != 0 || len(report.Manifests) != 0 {
		t.Fatalf("symlinked manifest was inventoried: %+v", report)
	}
}
