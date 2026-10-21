package analyze

import "testing"

func TestSupplementalGLSLStageSources(t *testing.T) {
	for _, name := range []string{
		"shader.comp", "shader.geom", "shader.tesc", "shader.tese",
		"shader.vsh", "shader.fsh", "COMPUTE.COMP", "mesh.GEOM",
	} {
		if got, ok := supplementalSourceLanguage(name); !ok || got != "GLSL" {
			t.Errorf("%q: got (%q, %v), want (GLSL, true)", name, got, ok)
		}
	}
	for _, name := range []string{"shader.comp.bak", "shader.geom~", "shader.spv", "shader.comp.txt"} {
		if got, ok := supplementalSourceLanguage(name); ok || got != "" {
			t.Errorf("%q: got (%q, %v), want no match", name, got, ok)
		}
	}
}
