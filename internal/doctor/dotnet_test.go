package doctor

import (
	"os"
	"path/filepath"
	"runtime"
	"strings"
	"testing"
)

func TestDotnetTestProjectMarkers(t *testing.T) {
	cases := []struct {
		name, content string
		want          bool
		invalid       bool
	}{
		{"explicit-true", `<Project><PropertyGroup><IsTestProject>true</IsTestProject></PropertyGroup></Project>`, true, false},
		{"test-sdk", `<Project><ItemGroup><PackageReference Include="Microsoft.NET.Test.Sdk" Version="17.12.0" /></ItemGroup></Project>`, true, false},
		{"sdk-update", `<Project><ItemGroup><PackageReference Update="microsoft.net.test.sdk" /></ItemGroup></Project>`, true, false},
		{"application", `<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><OutputType>Exe</OutputType></PropertyGroup></Project>`, false, false},
		{"comment-only", `<Project><!-- <IsTestProject>true</IsTestProject> --></Project>`, false, false},
		{"explicit-false", `<Project><PropertyGroup><IsTestProject>false</IsTestProject></PropertyGroup><ItemGroup><PackageReference Include="Microsoft.NET.Test.Sdk"/></ItemGroup></Project>`, false, false},
		{"malformed", `<Project><IsTestProject>true`, false, true},
	}
	for _, tt := range cases {
		t.Run(tt.name, func(t *testing.T) {
			dir := t.TempDir()
			if err := os.WriteFile(filepath.Join(dir, "Demo.csproj"), []byte(tt.content), 0600); err != nil {
				t.Fatal(err)
			}
			got, err := isDotnetTestProject(dir, "Demo.csproj")
			if (err != nil) != tt.invalid {
				t.Fatalf("err=%v, invalid=%v", err, tt.invalid)
			}
			if got != tt.want {
				t.Fatalf("isTest=%v, want=%v", got, tt.want)
			}
		})
	}
}

func TestDotnetProjectSymlinkCannotEscape(t *testing.T) {
	if runtime.GOOS == "windows" {
		t.Skip("symlinks depend on Windows privileges")
	}
	outside := filepath.Join(t.TempDir(), "outside.csproj")
	if err := os.WriteFile(outside, []byte(`<Project><IsTestProject>true</IsTestProject></Project>`), 0600); err != nil {
		t.Fatal(err)
	}
	root := t.TempDir()
	if err := os.Symlink(outside, filepath.Join(root, "Demo.csproj")); err != nil {
		t.Fatal(err)
	}
	got, err := isDotnetTestProject(root, "Demo.csproj")
	if got || err == nil || !strings.Contains(err.Error(), "regular file") {
		t.Fatalf("symlink was followed: got=%v err=%v", got, err)
	}
}

func TestInspectDotnetTestCommand(t *testing.T) {
	root := t.TempDir()
	if err := os.WriteFile(filepath.Join(root, "Example.Tests.csproj"), []byte(`<Project><PropertyGroup><IsTestProject>true</IsTestProject></PropertyGroup></Project>`), 0600); err != nil {
		t.Fatal(err)
	}
	report, err := Inspect(root)
	if err != nil {
		t.Fatal(err)
	}
	if report.Tests == nil || report.Tests.Executable != "dotnet" || strings.Join(report.Tests.Arguments, " ") != "test Example.Tests.csproj" {
		t.Fatalf(".NET test command was not discovered: %+v", report.Tests)
	}
}

func TestInspectDotnetNonTestProject(t *testing.T) {
	root := t.TempDir()
	if err := os.WriteFile(filepath.Join(root, "Example.csproj"), []byte(`<Project Sdk="Microsoft.NET.Sdk"/>`), 0600); err != nil {
		t.Fatal(err)
	}
	report, err := Inspect(root)
	if err != nil {
		t.Fatal(err)
	}
	if report.Tests != nil {
		t.Fatalf("non-test project incorrectly got a command: %+v", report.Tests)
	}
}
