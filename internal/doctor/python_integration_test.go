package doctor

import (
	"os"
	"path/filepath"
	"testing"
)

func TestPytestDiscoveryRequiresEvidence(t *testing.T) {
	dir := t.TempDir()
	if err := os.WriteFile(filepath.Join(dir, "pyproject.toml"), []byte("[project]\nname='not-a-pytest-project'\n"), 0600); err != nil {
		t.Fatal(err)
	}
	report, err := Inspect(dir)
	if err != nil {
		t.Fatal(err)
	}
	if report.Tests != nil {
		t.Fatalf("false-positive test command: %+v", report.Tests)
	}
	if err := os.WriteFile(filepath.Join(dir, "pytest.ini"), []byte("[pytest]\n"), 0600); err != nil {
		t.Fatal(err)
	}
	report, err = Inspect(dir)
	if err != nil {
		t.Fatal(err)
	}
	if report.Tests == nil || report.Tests.Executable != "python" {
		t.Fatalf("expected pytest test command: %+v", report.Tests)
	}
}
