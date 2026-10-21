package main

import (
    "bytes"
    "encoding/json"
    "os"
    "path/filepath"
    "strings"
    "testing"
)

func fixture(t *testing.T,root,name,body string) {
    t.Helper()
    if err:=os.WriteFile(filepath.Join(root,name),[]byte(body),0600);err!=nil {t.Fatal(err)}
}

func TestJavaScriptCandidatesNeverRunScripts(t *testing.T) {
    root:=t.TempDir()
    fixture(t,root,"package.json",`{"packageManager":"pnpm@9.0.0","scripts":{"dev":"echo private-value","test":"exit 33","build":"echo built","test;rm":"echo bad"}}`)
    fixture(t,root,"pnpm-lock.yaml","lockfileVersion: '9.0'")
    report,err:=discover(root)
    if err!=nil {t.Fatal(err)}
    if report.Status!="discovered" || len(report.Candidates)!=3 {t.Fatalf("report=%+v",report)}
    for _,item:=range report.Candidates {
        if !strings.HasPrefix(item.Command,"pnpm run ") || item.Verified {t.Fatalf("candidate=%+v",item)}
    }
    var out,errors bytes.Buffer
    if code:=run([]string{"-root",root,"-json"},&out,&errors);code!=0 {
        t.Fatalf("code=%d stderr=%s",code,errors.String())
    }
    var decoded Report
    if err:=json.Unmarshal(out.Bytes(),&decoded);err!=nil {t.Fatal(err)}
    if strings.Contains(out.String(),"private-value") || strings.Contains(out.String(),"test;rm") {
        t.Fatal("leaked script body or unsafe script name")
    }
}

func TestGoCargoMakefileCandidates(t *testing.T) {
    root:=t.TempDir()
    fixture(t,root,"go.mod","module example.org/demo\ngo 1.22\n")
    fixture(t,root,"Cargo.toml","[package]\nname='test'\n")
    fixture(t,root,"Makefile",".PHONY: test\ntest: example\n\t@exit 1\nlint:\n\t@echo lint\n")
    report,err:=discover(root)
    if err!=nil {t.Fatal(err)}
    if len(report.Candidates)!=6 {t.Fatalf("expected six commands; got %+v",report.Candidates)}
    for _,item:=range report.Candidates {if item.Verified {t.Fatal("incorrect verified flag")}}
}

func TestEmptyAndInvalidManifest(t *testing.T) {
    root:=t.TempDir()
    report,err:=discover(root)
    if err!=nil || report.Status!="no-manifest" || len(report.Candidates)!=0 {
        t.Fatalf("report=%+v error=%v",report,err)
    }
    fixture(t,root,"package.json","not valid JSON")
    if _,err:=discover(root);err==nil {t.Fatal("expected invalid JSON error")}
}

func TestConflictingLockfilesDoNotSelectManager(t *testing.T) {
    root:=t.TempDir()
    fixture(t,root,"package.json",`{"scripts":{"test":"echo test"}}`)
    fixture(t,root,"pnpm-lock.yaml","")
    fixture(t,root,"yarn.lock","")
    report,err:=discover(root)
    if err!=nil {t.Fatal(err)}
    if len(report.Candidates)!=0 || len(report.Warnings)==0 {t.Fatalf("report=%+v",report)}
}

func TestRejectsSymlinks(t *testing.T) {
    root:=t.TempDir()
    fixture(t,root,"actual","{}")
    if err:=os.Symlink("actual",filepath.Join(root,"package.json"));err!=nil {
        t.Skipf("symlinks unsupported: %v",err)
    }
    if _,err:=discover(root);err==nil {t.Fatal("expected symlink rejection")}
}

func TestArgumentErrors(t *testing.T) {
    var out,errors bytes.Buffer
    if code:=run([]string{"extra"},&out,&errors);code!=2 {t.Fatalf("code=%d",code)}
}
