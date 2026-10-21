package main

import (
	"bytes"
	"context"
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func makeSpec(t *testing.T, dir, name, content string) string {
	t.Helper()
	path := filepath.Join(dir, name)
	if err := os.MkdirAll(filepath.Dir(path), 0755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(path, []byte(content), 0644); err != nil {
		t.Fatal(err)
	}
	return path
}
func has(spec Specification, code string) bool {
	for _, f := range spec.Findings {
		if f.Code == code {
			return true
		}
	}
	return false
}

func TestEndpointsRefsAndDuplicateIDs(t *testing.T) {
	dir := t.TempDir()
	makeSpec(t, dir, "openapi.json", `{"openapi":"3.1.0","info":{"title":"Shop"},"paths":{"/orders":{"get":{"operationId":"list"},"post":{"operationId":"list"}},"/users":{"get":{"responses":{"200":{"$ref":"#/components/responses/Found"}},"parameters":[{"$ref":"#/components/parameters/Missing"}]}}},"components":{"responses":{"Found":{"description":"ok"}}}}`)
	r, err := scan(context.Background(), dir)
	if err != nil {
		t.Fatal(err)
	}
	if len(r.Specifications) != 1 {
		t.Fatalf("spec count: %+v", r)
	}
	spec := r.Specifications[0]
	if spec.Version != "3.1.0" || spec.Title != "Shop" || len(spec.Endpoints) != 3 {
		t.Fatalf("incorrect inventory: %+v", spec)
	}
	if !has(spec, "LOCAL_REF_MISSING") || !has(spec, "OPERATION_ID_DUPLICATE") {
		t.Fatalf("expected warnings: %+v", spec.Findings)
	}
	if spec.Endpoints[0].Method != "GET" || spec.Endpoints[0].Path != "/orders" {
		t.Fatal("non-deterministic order")
	}
}
func TestLocalPointerEscapes(t *testing.T) {
	doc := map[string]any{"a/b": map[string]any{"x~y": []any{1.0}}}
	if !resolvePointer(doc, "#/a~1b/x~0y/0") {
		t.Fatal("escaped pointer not resolved")
	}
	if resolvePointer(doc, "#/a~2b") {
		t.Fatal("invalid escape accepted")
	}
	if resolvePointer(doc, "https://example.org/remote") {
		t.Fatal("external pointer accepted")
	}
}
func TestNoNetworkAccessForExternalReference(t *testing.T) {
	path := makeSpec(t, t.TempDir(), "swagger.json", `{"swagger":"2.0","paths":{"/items":{"get":{"responses":{"200":{"schema":{"$ref":"https://invalid.example.com/never-fetch"}}}}}}}`)
	spec := analyzeFile(path)
	if len(spec.Endpoints) != 1 || !has(spec, "EXTERNAL_REF_NOT_CHECKED") {
		t.Fatalf("external ref: %+v", spec)
	}
}
func TestMalformedAndOversizedSpecs(t *testing.T) {
	dir := t.TempDir()
	path := makeSpec(t, dir, "openapi.json", "not json")
	if !has(analyzeFile(path), "INVALID_JSON") {
		t.Fatal("syntax error undetected")
	}
	if err := os.WriteFile(path, bytes.Repeat([]byte("x"), maxFileBytes+1), 0644); err != nil {
		t.Fatal(err)
	}
	if !has(analyzeFile(path), "SPEC_TOO_LARGE") {
		t.Fatal("size limit undetected")
	}
}
func TestDirectoryDoesNotFollowSymlinksOrVendor(t *testing.T) {
	dir := t.TempDir()
	outside := t.TempDir()
	makeSpec(t, outside, "openapi.json", `{"openapi":"3.0.0","paths":{}}`)
	if err := os.Symlink(filepath.Join(outside, "openapi.json"), filepath.Join(dir, "openapi.json")); err != nil {
		t.Skipf("symlinks unsupported: %v", err)
	}
	makeSpec(t, dir, "node_modules/openapi.json", "{}")
	r, err := scan(context.Background(), dir)
	if err != nil {
		t.Fatal(err)
	}
	if len(r.Specifications) != 0 {
		t.Fatal("followed symlink or vendor")
	}
}
func TestMachineOutputAndStrict(t *testing.T) {
	dir := t.TempDir()
	makeSpec(t, dir, "openapi.json", `{"openapi":"3.0.0","paths":{"/x":{"get":{"operationId":"same"},"post":{"operationId":"same"}}}}`)
	var out, stderr bytes.Buffer
	if exit := run(context.Background(), []string{"--json", dir}, &out, &stderr); exit != 0 {
		t.Fatalf("exit: %d stderr:%s", exit, stderr.String())
	}
	var doc Result
	if err := json.Unmarshal(out.Bytes(), &doc); err != nil {
		t.Fatal(err)
	}
	if len(doc.Specifications) != 1 {
		t.Fatal("missing result")
	}
	if exit := run(context.Background(), []string{"--strict", dir}, &out, &stderr); exit != 1 {
		t.Fatal("strict mode didn't fail warnings")
	}
}
func TestInvalidArgsAndUnsupported(t *testing.T) {
	var out, stderr bytes.Buffer
	if exit := run(context.Background(), []string{"a", "b"}, &out, &stderr); exit != 2 {
		t.Fatal("expected invocation error")
	}
	path := makeSpec(t, t.TempDir(), "openapi.json", `{"openapi":"4.0.0","paths":{}}`)
	if !has(analyzeFile(path), "VERSION_UNSUPPORTED") {
		t.Fatal("version accepted")
	}
	if strings.Contains(out.String(), "secret") {
		t.Fatal("unexpected output")
	}
}
func TestCancellation(t *testing.T) {
	ctx, cancel := context.WithCancel(context.Background())
	cancel()
	_, err := scan(ctx, t.TempDir())
	if err == nil {
		t.Fatal("expected cancelled scan")
	}
}
