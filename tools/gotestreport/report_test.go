package main

import (
	"bytes"
	"encoding/json"
	"strings"
	"testing"
)

func TestSummarizesNestedFailureAndSkipsWithoutLeakingOutput(t *testing.T) {
	input := strings.Join([]string{
		`{"Action":"start","Package":"example.com/a"}`,
		`{"Action":"run","Package":"example.com/a","Test":"TestMain"}`,
		`{"Action":"output","Package":"example.com/a","Test":"TestMain","Output":"PASSWORD=secret-123\n"}`,
		`{"Action":"fail","Package":"example.com/a","Test":"TestMain"}`,
		`{"Action":"run","Package":"example.com/a","Test":"TestSkipped"}`,
		`{"Action":"skip","Package":"example.com/a","Test":"TestSkipped"}`,
		`{"Action":"fail","Package":"example.com/a"}`,
		`{"Action":"start","Package":"example.com/b"}`,
		`{"Action":"pass","Package":"example.com/b"}`,
	}, "\n") + "\n"
	var stdout, stderr bytes.Buffer
	exit := run([]string{"-format", "json"}, strings.NewReader(input), &stdout, &stderr)
	if exit != 1 {
		t.Fatalf("exit=%d err=%q", exit, stderr.String())
	}
	var result Report
	if err := json.Unmarshal(stdout.Bytes(), &result); err != nil {
		t.Fatal(err)
	}
	if result.Status != "failed" || result.Packages != 2 || result.FailedTests != 1 || result.SkippedTests != 1 || len(result.Failures) != 1 {
		t.Fatalf("unexpected result: %+v", result)
	}
	if bytes.Contains(stdout.Bytes(), []byte("secret-123")) {
		t.Fatal("test output leaked")
	}
}

func TestPassingSuite(t *testing.T) {
	input := `{"Action":"pass","Package":"example.com/p","Test":"TestPass"}` + "\n" + `{"Action":"pass","Package":"example.com/p"}` + "\n"
	report, err := Analyze(strings.NewReader(input))
	if err != nil || report.Status != "passed" || report.PassedTests != 1 {
		t.Fatalf("report=%+v err=%v", report, err)
	}
}

func TestBuildFailureIsPackageFailure(t *testing.T) {
	input := `{"Action":"output","Package":"example.com/p","Output":"compiler error with secret\n"}` + "\n" + `{"Action":"fail","Package":"example.com/p"}` + "\n"
	report, err := Analyze(strings.NewReader(input))
	if err != nil || len(report.Failures) != 1 || report.Failures[0].Kind != "package" {
		t.Fatalf("report=%+v err=%v", report, err)
	}
}

func TestIncompleteAndInvalidStreams(t *testing.T) {
	incomplete := `{"Action":"run","Package":"example.com/p","Test":"TestOne"}` + "\n"
	var out, errOut bytes.Buffer
	if exit := run(nil, strings.NewReader(incomplete), &out, &errOut); exit != 2 {
		t.Fatalf("incomplete exit=%d", exit)
	}
	for _, input := range []string{"", "not-json\n", `{"Action":"pass","Package":""}` + "\n", `{"Action":"pass","Package":"example"}` + "\n" + "garbage\n"} {
		if _, err := Analyze(strings.NewReader(input)); err == nil {
			t.Fatalf("expected failure for %q", input)
		}
	}
}

func TestDeterministicOrderAndTerminalControlEscaping(t *testing.T) {
	input := `{"Action":"fail","Package":"example.com/z"}` + "\n" + `{"Action":"fail","Package":"example.com/a"}` + "\n"
	var out, errOut bytes.Buffer
	if n := run(nil, strings.NewReader(input), &out, &errOut); n != 1 {
		t.Fatal(n)
	}
	if strings.Index(out.String(), "example.com/a") > strings.Index(out.String(), "example.com/z") {
		t.Fatal(out.String())
	}
	control := `{"Action":"fail","Package":"pkg\u001b[31m"}` + "\n"
	out.Reset()
	if n := run(nil, strings.NewReader(control), &out, &errOut); n != 1 {
		t.Fatal(n)
	}
	if strings.Contains(out.String(), "\x1b") {
		t.Fatal("terminal escape printed")
	}
}

func TestHugeEventLimit(t *testing.T) {
	_, err := Analyze(strings.NewReader(`{"Action":"output","Package":"p","Output":"` + strings.Repeat("x", 2<<20) + `"}`))
	if err == nil {
		t.Fatal("expected size limit error")
	}
}
