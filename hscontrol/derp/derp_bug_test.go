package derp

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"net/url"
	"os"
	"path/filepath"
	"testing"

	"github.com/juanfont/headscale/hscontrol/types"
	"tailscale.com/tailcfg"
)

// TestGetDERPMap_BothURLAndPath checks that a map fetched over HTTP and one
// read from a file are both present in the merged result.
//
// Both sources are built by the test itself: the URL is served by an
// httptest server, the file comes from a temporary directory. GetDERPMap
// processes URLs before paths and returns on the first error, so a test that
// reaches out to the network or reads a fixed /tmp path is really asserting
// on the environment rather than on the merge.
func TestGetDERPMap_BothURLAndPath(t *testing.T) {
	urlMap := &tailcfg.DERPMap{
		Regions: map[int]*tailcfg.DERPRegion{
			1: {
				RegionID:   1,
				RegionCode: "nyc",
				RegionName: "New York",
				Nodes: []*tailcfg.DERPNode{
					{
						Name:     "1a",
						RegionID: 1,
						HostName: "derp1.example.com",
					},
				},
			},
		},
	}

	body, err := json.Marshal(urlMap)
	if err != nil {
		t.Fatalf("marshalling DERP map for the test server: %v", err)
	}

	server := httptest.NewServer(http.HandlerFunc(
		func(w http.ResponseWriter, _ *http.Request) {
			w.Header().Set("Content-Type", "application/json")
			_, _ = w.Write(body)
		},
	))
	defer server.Close()

	serverURL, err := url.Parse(server.URL)
	if err != nil {
		t.Fatalf("parsing test server URL: %v", err)
	}

	derpPath := filepath.Join(t.TempDir(), "derp.yaml")

	// Keys are lowercase: tailcfg has no yaml tags, so yaml.v3 falls back to
	// the lowercased field names. Shape follows derp-example.yaml.
	const derpYAML = `regions:
  900:
    regionid: 900
    regioncode: test-derp
    regionname: Test Region
    nodes:
      - name: 900a
        regionid: 900
        hostname: derp900.example.com
`

	if err := os.WriteFile(derpPath, []byte(derpYAML), 0o600); err != nil {
		t.Fatalf("writing DERP map: %v", err)
	}

	dm, err := GetDERPMap(types.DERPConfig{
		URLs:  []url.URL{*serverURL},
		Paths: []string{derpPath},
	})
	if err != nil {
		t.Fatalf("GetDERPMap: %v", err)
	}

	var hasURLRegion, hasPathRegion bool

	for _, region := range dm.Regions {
		switch region.RegionCode {
		case "nyc":
			hasURLRegion = true
		case "test-derp":
			hasPathRegion = true
		}
	}

	if !hasURLRegion {
		t.Error("region served over HTTP is missing from the merged map")
	}

	if !hasPathRegion {
		t.Error("region read from the file is missing from the merged map")
	}
}
