// devpilot-openapi discovers documented API endpoints from local OpenAPI JSON files.
// It never executes repository code, invokes external tools, or accesses the network.
package main

import (
	"context"
	"encoding/json"
	"errors"
	"flag"
	"fmt"
	"io"
	"io/fs"
	"net/url"
	"os"
	"os/signal"
	"path/filepath"
	"sort"
	"strconv"
	"strings"
)

const maxFileBytes = 5 << 20
const maxEntries = 20000
const maxSpecFiles = 64
const maxNodes = 150000

type Endpoint struct {
	Method      string `json:"method"`
	Path        string `json:"path"`
	OperationID string `json:"operation_id,omitempty"`
}

type Finding struct {
	Code     string `json:"code"`
	Level    string `json:"level"`
	Evidence string `json:"evidence"`
	Remedy   string `json:"remedy"`
}

type Specification struct {
	File      string     `json:"file"`
	Version   string     `json:"version,omitempty"`
	Title     string     `json:"title,omitempty"`
	Endpoints []Endpoint `json:"endpoints"`
	Findings  []Finding  `json:"findings"`
}

type Result struct {
	Target         string          `json:"target"`
	Specifications []Specification `json:"specifications"`
	Findings       []Finding       `json:"findings"`
}

var methods = map[string]bool{"get": true, "post": true, "put": true, "patch": true, "delete": true, "options": true, "head": true, "trace": true}
var ignore = map[string]bool{".git": true, ".venv": true, "node_modules": true, "vendor": true, "dist": true, "build": true, "target": true, "bin": true, "obj": true, "coverage": true}

func main() {
	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt)
	defer stop()
	os.Exit(run(ctx, os.Args[1:], os.Stdout, os.Stderr))
}

func run(ctx context.Context, args []string, stdout, stderr io.Writer) int {
	flags := flag.NewFlagSet("devpilot-openapi", flag.ContinueOnError)
	flags.SetOutput(stderr)
	asJSON := flags.Bool("json", false, "emit machine-readable JSON")
	strict := flags.Bool("strict", false, "fail when evidence-based warnings are present")
	if err := flags.Parse(args); err != nil {
		return 2
	}
	if len(flags.Args()) > 1 {
		fmt.Fprintln(stderr, "usage: devpilot-openapi [--json] [--strict] [spec.json | project-directory]")
		return 2
	}
	target := "."
	if len(flags.Args()) == 1 {
		target = flags.Args()[0]
	}
	result, err := scan(ctx, target)
	if err != nil {
		fmt.Fprintln(stderr, "openapi:", err)
		return 1
	}
	if *asJSON {
		encoder := json.NewEncoder(stdout)
		encoder.SetIndent("", "  ")
		if err := encoder.Encode(result); err != nil {
			fmt.Fprintln(stderr, err)
			return 1
		}
	} else {
		printText(stdout, result)
	}
	for _, f := range result.Findings {
		if f.Level == "error" || *strict && f.Level == "warning" {
			return 1
		}
	}
	for _, spec := range result.Specifications {
		for _, f := range spec.Findings {
			if f.Level == "error" || *strict && f.Level == "warning" {
				return 1
			}
		}
	}
	return 0
}

func scan(ctx context.Context, input string) (Result, error) {
	abs, err := filepath.Abs(input)
	if err != nil {
		return Result{}, err
	}
	info, err := os.Lstat(abs)
	if err != nil {
		return Result{}, err
	}
	if info.Mode()&os.ModeSymlink != 0 {
		return Result{}, errors.New("refusing a symbolic-link target")
	}
	result := Result{Target: abs, Specifications: []Specification{}, Findings: []Finding{}}
	paths := []string{}
	if info.Mode().IsRegular() {
		paths = append(paths, abs)
	} else if info.IsDir() {
		count := 0
		err := filepath.WalkDir(abs, func(path string, entry fs.DirEntry, walkErr error) error {
			if walkErr != nil {
				return walkErr
			}
			if err := ctx.Err(); err != nil {
				return err
			}
			if path == abs {
				return nil
			}
			count++
			if count > maxEntries {
				return errors.New("scan limit reached (20,000 entries)")
			}
			rel, err := filepath.Rel(abs, path)
			if err != nil {
				return err
			}
			depth := strings.Count(filepath.ToSlash(rel), "/") + 1
			if entry.IsDir() {
				if depth > 4 || ignore[entry.Name()] || strings.HasPrefix(entry.Name(), ".") {
					return filepath.SkipDir
				}
				return nil
			}
			if entry.Type().IsRegular() && depth <= 5 && isCandidate(entry.Name()) {
				paths = append(paths, path)
				if len(paths) > maxSpecFiles {
					return errors.New("more than 64 OpenAPI candidate files found")
				}
			}
			return nil
		})
		if err != nil {
			return result, fmt.Errorf("walk project: %w", err)
		}
	} else {
		return result, errors.New("target must be a regular JSON file or directory")
	}
	sort.Strings(paths)
	if len(paths) == 0 {
		result.Findings = append(result.Findings, Finding{"NO_OPENAPI_SPEC", "info", "No OpenAPI JSON spec found at scan depth", "Provide a spec filename or place openapi.json / swagger.json in the project."})
	}
	for _, path := range paths {
		if err := ctx.Err(); err != nil {
			return result, err
		}
		spec := analyzeFile(path)
		if info.IsDir() {
			rel, err := filepath.Rel(abs, path)
			if err == nil {
				spec.File = filepath.ToSlash(rel)
			}
		}
		result.Specifications = append(result.Specifications, spec)
	}
	return result, nil
}

func isCandidate(name string) bool {
	name = strings.ToLower(name)
	if !strings.HasSuffix(name, ".json") {
		return false
	}
	return strings.HasPrefix(name, "openapi") || strings.HasPrefix(name, "swagger")
}

func analyzeFile(path string) Specification {
	spec := Specification{File: path, Endpoints: []Endpoint{}, Findings: []Finding{}}
	add := func(code, level, evidence, remedy string) {
		spec.Findings = append(spec.Findings, Finding{code, level, evidence, remedy})
	}
	info, err := os.Lstat(path)
	if err != nil || !info.Mode().IsRegular() {
		add("SPEC_NOT_REGULAR", "error", "File cannot be read as a regular file", "Use a regular local JSON file, not a symlink.")
		return spec
	}
	if info.Size() > maxFileBytes {
		add("SPEC_TOO_LARGE", "error", "Specification exceeds 5 MiB", "Inspect a smaller local spec; large specs are not analyzed.")
		return spec
	}
	file, err := os.Open(path)
	if err != nil {
		add("SPEC_UNREADABLE", "error", err.Error(), "Check file permissions.")
		return spec
	}
	defer file.Close()
	dec := json.NewDecoder(io.LimitReader(file, maxFileBytes+1))
	var root any
	if err := dec.Decode(&root); err != nil {
		add("INVALID_JSON", "error", err.Error(), "Fix the JSON syntax.")
		return spec
	}
	var trailing any
	if err := dec.Decode(&trailing); err != io.EOF {
		add("INVALID_JSON", "error", "Multiple JSON values or oversized input", "Ensure the file contains exactly one JSON document (max 5 MiB).")
		return spec
	}
	object, ok := root.(map[string]any)
	if !ok {
		add("INVALID_SPEC", "error", "Top-level JSON value is not an object", "Use an OpenAPI specification object.")
		return spec
	}
	if v, ok := object["openapi"].(string); ok && strings.HasPrefix(v, "3.") {
		spec.Version = v
	} else if v, ok := object["swagger"].(string); ok && v == "2.0" {
		spec.Version = v
	} else {
		add("VERSION_UNSUPPORTED", "error", "Missing or unsupported OpenAPI version", "Provide an OpenAPI 3.x or Swagger 2.0 JSON document.")
	}
	if metadata, ok := object["info"].(map[string]any); ok {
		spec.Title, _ = metadata["title"].(string)
	}
	pathObj, ok := object["paths"].(map[string]any)
	if !ok {
		add("PATHS_MISSING", "warning", "No paths object found", "Document available routes under paths.")
	} else {
		ids := map[string]string{}
		routeNames := make([]string, 0, len(pathObj))
		for route := range pathObj {
			routeNames = append(routeNames, route)
		}
		sort.Strings(routeNames)
		for _, route := range routeNames {
			if !strings.HasPrefix(route, "/") {
				add("PATH_INVALID", "warning", "Path does not start with /: "+route, "Use absolute OpenAPI path keys.")
			}
			operations, ok := pathObj[route].(map[string]any)
			if !ok {
				add("PATH_ITEM_INVALID", "warning", "Path item is not an object: "+route, "Use a Path Item object.")
				continue
			}
			for _, method := range []string{"get", "post", "put", "patch", "delete", "options", "head", "trace"} {
				val, exists := operations[method]
				if !exists {
					continue
				}
				op, ok := val.(map[string]any)
				if !ok {
					add("OPERATION_INVALID", "warning", strings.ToUpper(method)+" "+route+" is not an object", "Provide a valid Operation object.")
					continue
				}
				id, _ := op["operationId"].(string)
				if id != "" {
					if previous, exists := ids[id]; exists {
						add("OPERATION_ID_DUPLICATE", "warning", "operationId "+id+" is used by "+previous+" and "+strings.ToUpper(method)+" "+route, "Assign unique operationId values.")
					} else {
						ids[id] = strings.ToUpper(method) + " " + route
					}
				}
				spec.Endpoints = append(spec.Endpoints, Endpoint{strings.ToUpper(method), route, id})
			}
		}
	}
	visited := 0
	externalRefs := 0
	var traverse func(value any, location string)
	traverse = func(value any, location string) {
		visited++
		if visited > maxNodes {
			return
		}
		switch x := value.(type) {
		case map[string]any:
			keys := make([]string, 0, len(x))
			for key := range x {
				keys = append(keys, key)
			}
			sort.Strings(keys)
			for _, key := range keys {
				v := x[key]
				if key == "$ref" {
					if ref, ok := v.(string); ok {
						if strings.HasPrefix(ref, "#") {
							if !resolvePointer(root, ref) {
								add("LOCAL_REF_MISSING", "warning", location+" -> "+ref, "Correct the local JSON Pointer reference.")
							}
						} else {
							externalRefs++
						}
					}
				}
				traverse(v, location+"/"+strings.ReplaceAll(strings.ReplaceAll(key, "~", "~0"), "/", "~1"))
			}
		case []any:
			for i, v := range x {
				traverse(v, location+"/"+strconv.Itoa(i))
			}
		}
	}
	traverse(root, "#")
	if visited > maxNodes {
		add("SPEC_COMPLEXITY_LIMIT", "warning", "Reference walk exceeded 150,000 JSON nodes", "Split the specification or reduce deeply nested schemas.")
	}
	if externalRefs > 0 {
		add("EXTERNAL_REF_NOT_CHECKED", "info", fmt.Sprintf("%d external $ref entries were not dereferenced", externalRefs), "Validate external references with a trusted tool if needed.")
	}
	sort.Slice(spec.Findings, func(i, j int) bool {
		if spec.Findings[i].Code == spec.Findings[j].Code {
			return spec.Findings[i].Evidence < spec.Findings[j].Evidence
		}
		return spec.Findings[i].Code < spec.Findings[j].Code
	})
	return spec
}

func resolvePointer(document any, ref string) bool {
	if ref == "#" {
		return true
	}
	if !strings.HasPrefix(ref, "#/") {
		return false
	}
	decoded, err := url.PathUnescape(ref[1:])
	if err != nil {
		return false
	}
	for _, segment := range strings.Split(decoded[1:], "/") {
		// JSON Pointer escape order matters: ~1 becomes '/', then ~0 becomes '~'.
		if strings.Contains(strings.ReplaceAll(strings.ReplaceAll(segment, "~1", ""), "~0", ""), "~") {
			return false
		}
		segment = strings.ReplaceAll(strings.ReplaceAll(segment, "~1", "/"), "~0", "~")
		switch v := document.(type) {
		case map[string]any:
			next, ok := v[segment]
			if !ok {
				return false
			}
			document = next
		case []any:
			idx, err := strconv.Atoi(segment)
			if err != nil || idx < 0 || idx >= len(v) {
				return false
			}
			document = v[idx]
		default:
			return false
		}
	}
	return true
}

func printText(out io.Writer, result Result) {
	fmt.Fprintln(out, "DevPilot OpenAPI Inspector")
	fmt.Fprintln(out, "Target:", result.Target)
	for _, f := range result.Findings {
		fmt.Fprintf(out, "[%s] %s: %s\n  Next: %s\n", f.Level, f.Code, f.Evidence, f.Remedy)
	}
	for _, spec := range result.Specifications {
		fmt.Fprintf(out, "\n%s (OpenAPI %s): %d endpoints\n", spec.File, spec.Version, len(spec.Endpoints))
		for _, endpoint := range spec.Endpoints {
			fmt.Fprintf(out, "  %-7s %s", endpoint.Method, endpoint.Path)
			if endpoint.OperationID != "" {
				fmt.Fprint(out, "  [", endpoint.OperationID, "]")
			}
			fmt.Fprintln(out)
		}
		for _, f := range spec.Findings {
			fmt.Fprintf(out, "[%s] %s: %s\n  Next: %s\n", f.Level, f.Code, f.Evidence, f.Remedy)
		}
	}
	fmt.Fprintln(out, "Inspection is read-only. No requests were sent and external references were not fetched.")
}
