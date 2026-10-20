package sarif

import (
	"encoding/json"
	"strings"
	"testing"
)

func TestSARIFShapeAndLevels(t *testing.T) {
	doc := Build([]Finding{
		{"pass", "tool-go", "Go is available", ""},
		{"info", "z-info", "No project found", "Check directory"},
		{"warning", "a-lock", "Conflicting lockfiles", "Keep one"},
		{"error", "a-lock", "Bad lockfile", "Fix it"},
		{"unknown", "invalid", "Not a valid finding", ""},
	})
	if doc.Version != "2.1.0" || len(doc.Runs) != 1 || doc.Runs[0].Tool.Driver.Name != "DevPilot" {
		t.Fatalf("bad log shape: %+v", doc)
	}
	r := doc.Runs[0]
	if len(r.Results) != 3 || len(r.Tool.Driver.Rules) != 2 {
		t.Fatalf("bad filtering/dedup: %+v", r)
	}
	if r.Results[0].Level != "note" || r.Results[1].Level != "warning" || r.Results[2].Level != "error" {
		t.Fatalf("bad severity: %+v", r.Results)
	}
	if r.Tool.Driver.Rules[0].ID != "a-lock" || r.Tool.Driver.Rules[1].ID != "z-info" {
		t.Fatal("unstable rule order")
	}
	if r.Results[1].Properties == nil || r.Results[1].Properties.Remedy != "Keep one" {
		t.Fatal("missing remedy")
	}
	b, err := json.Marshal(doc)
	if err != nil {
		t.Fatal(err)
	}
	if strings.Contains(string(b), "tool-go") || strings.Contains(string(b), "\"locations\"") {
		t.Fatalf("invented a pass or file location: %s", b)
	}
}
func TestEmptyAndJSONEscaping(t *testing.T) {
	doc := Build([]Finding{{"warning", "escape", "a <script> & \"quoted\"", ""}, {"warning", "", "invalid", ""}})
	b, err := json.Marshal(doc)
	if err != nil {
		t.Fatal(err)
	}
	if !json.Valid(b) || !strings.Contains(string(b), "\\u003cscript\\u003e") {
		t.Fatalf("invalid escaped JSON: %s", b)
	}
	empty := Build(nil)
	if len(empty.Runs[0].Results) != 0 || len(empty.Runs[0].Tool.Driver.Rules) != 0 {
		t.Fatal("empty report must have empty arrays")
	}
	b, err = json.Marshal(empty)
	if err != nil || strings.Contains(string(b), "\"results\":null") || strings.Contains(string(b), "\"rules\":null") {
		t.Fatalf("null array: %s %v", b, err)
	}
}
func TestBuildDeterministic(t *testing.T) {
	input := []Finding{{"warning", "z", "foo", ""}, {"warning", "a", "bar", ""}}
	first, _ := json.Marshal(Build(input))
	second, _ := json.Marshal(Build(input))
	if string(first) != string(second) {
		t.Fatalf("not deterministic: %s vs %s", first, second)
	}
}
