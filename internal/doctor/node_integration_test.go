package doctor

import "testing"

func TestInvalidNodePackageManagerReported(t *testing.T) {
	root := t.TempDir()
	write(t, root, "package.json", `{"packageManager":"unexpected-runner@1.0","scripts":{"test":"echo testing"}}`)
	report, err := Inspect(root)
	if err != nil {
		t.Fatal(err)
	}
	if !finding(report, "package-manager-invalid") || !report.HasWarnings() {
		t.Fatalf("invalid executable must generate warning: %+v", report.Findings)
	}
	if report.PackageManager != "npm" || report.Tests == nil || report.Tests.Executable != "npm" {
		t.Fatalf("unsafe package manager was selected: %+v", report)
	}
}
