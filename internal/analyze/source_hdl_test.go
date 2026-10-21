package analyze

import "testing"

func TestSupplementalHDLSourceLanguage(t *testing.T) {
	cases := []struct {
		name, language string
	}{
		{"logic.vhd", "VHDL"},
		{"entity.VHDL", "VHDL"},
		{"testbench.sv", "SystemVerilog"},
		{"defs.SVH", "SystemVerilog"},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			got, ok := supplementalSourceLanguage(tc.name)
			if !ok || got != tc.language {
				t.Fatalf("supplementalSourceLanguage(%q) = %q, %v; want %q, true", tc.name, got, ok, tc.language)
			}
		})
	}
}

func TestSupplementalHDLDoesNotGuessAmbiguousOrBackupFiles(t *testing.T) {
	for _, name := range []string{"design.v", "defs.vh", "entity.vhd.bak", "tb.sv~", "README.md"} {
		t.Run(name, func(t *testing.T) {
			if got, ok := supplementalSourceLanguage(name); ok {
				t.Fatalf("unexpected language classification for %q: %q", name, got)
			}
		})
	}
}
