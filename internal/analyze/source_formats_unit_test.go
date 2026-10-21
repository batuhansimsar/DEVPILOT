package analyze

import "testing"

func TestSupplementalSourceLanguage(t *testing.T) {
	cases := []struct {
		filename, want string
		recognized     bool
	}{
		{"analysis.ipynb", "Jupyter Notebook", true},
		{"NOTEBOOK.IPYNB", "Jupyter Notebook", true},
		{"api.proto", "Protocol Buffers", true},
		{"schema.graphql", "GraphQL", true},
		{"queries.GQL", "GraphQL", true},
		{"contract.sol", "Solidity", true},
		{"flake.nix", "Nix", true},
		{"schema.graphql.bak", "", false},
		{"README.md", "", false},
		{".ipynb", "Jupyter Notebook", true},
	}
	for _, tc := range cases {
		t.Run(tc.filename, func(t *testing.T) {
			got, ok := supplementalSourceLanguage(tc.filename)
			if ok != tc.recognized || got != tc.want {
				t.Fatalf("supplementalSourceLanguage(%q) = %q, %v; want %q, %v", tc.filename, got, ok, tc.want, tc.recognized)
			}
		})
	}
}
