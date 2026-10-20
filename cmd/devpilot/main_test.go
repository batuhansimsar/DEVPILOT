package main

import (
	"bytes"
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func runCommand(args ...string) (int,string,string) {
	var stdout,stderr bytes.Buffer
	code:=run(args,&stdout,&stderr)
	return code,stdout.String(),stderr.String()
}

func TestDoctorJSONAndStrict(t *testing.T) {
	root:=t.TempDir()
	if err:=os.WriteFile(filepath.Join(root,"package.json"),[]byte(`{"scripts":`),0644);err!=nil {t.Fatal(err)}
	code,stdout,stderr:=runCommand("doctor","--json",root)
	if code!=0 || stderr!="" {t.Fatalf("code=%d stderr=%s",code,stderr)}
	var result struct {Findings []struct {Code string `json:"code"`} `json:"findings"`}
	if err:=json.Unmarshal([]byte(stdout),&result);err!=nil {t.Fatal(err)}
	if len(result.Findings)==0 {t.Fatal("expected findings")}
	code,_,_=runCommand("doctor","--strict",root)
	if code!=1 {t.Fatalf("strict should fail: %d",code)}
}

func TestExecutionIsBlockedWithoutTrust(t *testing.T) {
	root:=t.TempDir()
	if err:=os.WriteFile(filepath.Join(root,"package.json"),[]byte(`{"scripts":{"test":"node -e \"process.exit(0)\""}}`),0644);err!=nil {t.Fatal(err)}
	code,_,stderr:=runCommand("test","--run",root)
	if code!=2 || !strings.Contains(stderr,"Refusing") {t.Fatalf("code=%d stderr=%s",code,stderr)}
	code,stdout,_:=runCommand("test",root)
	if code!=0 || !strings.Contains(stdout,"node:.") {t.Fatalf("code=%d output=%s",code,stdout)}
}

func TestInvalidInputs(t *testing.T) {
	if code,_,_:=runCommand("bad");code!=2 {t.Fatal(code)}
	if code,_,_:=runCommand("doctor","missing","extra");code!=2 {t.Fatal(code)}
	if code,_,_:=runCommand("test","--timeout=0s");code!=2 {t.Fatal(code)}
}
