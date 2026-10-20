package doctor

import (
	"bytes"
	"encoding/xml"
	"io"
	"strings"
)

// isDotnetTestProject looks for explicit test-project evidence in an MSBuild
// project file. It parses XML instead of searching text so comments cannot
// accidentally enable test execution. It never evaluates MSBuild properties.
func isDotnetTestProject(root, name string) (bool, error) {
	data, present, err := readMarker(root, name)
	if err != nil || !present {
		return false, err
	}

	decoder := xml.NewDecoder(bytes.NewReader(data))
	var isTest, explicitlyNotTest, hasTestSDK bool
	for {
		token, err := decoder.Token()
		if err == io.EOF {
			break
		}
		if err != nil {
			return false, err
		}
		element, ok := token.(xml.StartElement)
		if !ok {
			continue
		}
		switch element.Name.Local {
		case "IsTestProject":
			var value string
			if err := decoder.DecodeElement(&value, &element); err != nil {
				return false, err
			}
			switch strings.ToLower(strings.TrimSpace(value)) {
			case "true":
				isTest = true
			case "false":
				explicitlyNotTest = true
			}
		case "PackageReference":
			for _, attr := range element.Attr {
				if (attr.Name.Local == "Include" || attr.Name.Local == "Update") &&
					strings.EqualFold(strings.TrimSpace(attr.Value), "Microsoft.NET.Test.Sdk") {
					hasTestSDK = true
				}
			}
		}
	}
	// Explicitly disabling the test project takes precedence over SDK hints.
	return !explicitlyNotTest && (isTest || hasTestSDK), nil
}
