package hscontrol

import (
	"context"
	"os"
	"path/filepath"
	"testing"
	"time"

	v1 "github.com/juanfont/headscale/gen/go/headscale/v1"
	"github.com/juanfont/headscale/hscontrol/mapper"
	"github.com/juanfont/headscale/hscontrol/types"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

// fileModePolicy is valid HuJSON that strict JSON rejects: a comment and a
// trailing comma inside an array. Storing it must not reformat, reorder or
// strip anything, the file has to hold these exact bytes.
const fileModePolicy = `{
    // comments and trailing commas are HuJSON, not JSON
    "randomizeClientPort": true,
    "acls": [
        {"action": "accept", "src": ["*"], "dst": ["*:*"]},
    ]
}
`

// createFileModeTestApp mirrors [createTestApp] but points the policy at a
// file, as a deployment with policy.mode: file does. The existing helper
// hardcodes [types.PolicyModeDB] and is left alone.
func createFileModeTestApp(t *testing.T, policyPath string) *Headscale {
	t.Helper()

	tmpDir := t.TempDir()

	cfg := types.Config{
		ServerURL:           "http://localhost:8080",
		NoisePrivateKeyPath: tmpDir + "/noise_private.key",
		Database: types.DatabaseConfig{
			Type: "sqlite3",
			Sqlite: types.SqliteConfig{
				Path: tmpDir + "/headscale_test.db",
			},
		},
		OIDC: types.OIDCConfig{},
		Policy: types.PolicyConfig{
			Mode: types.PolicyModeFile,
			Path: policyPath,
		},
		Tuning: types.Tuning{
			BatchChangeDelay: 100 * time.Millisecond,
			BatcherWorkers:   1,
		},
	}

	app, err := NewHeadscale(&cfg)
	require.NoError(t, err)

	app.mapBatcher = mapper.NewBatcherAndMapper(&cfg, app.state)
	app.mapBatcher.Start()

	t.Cleanup(func() {
		if app.mapBatcher != nil {
			app.mapBatcher.Close()
		}
	})

	return app
}

// TestSetPolicyFileModeWritesPolicyFile checks that a policy sent over the API
// lands in policy.path byte for byte, and that the permissions of an existing
// file survive the rewrite.
func TestSetPolicyFileModeWritesPolicyFile(t *testing.T) {
	t.Parallel()

	path := filepath.Join(t.TempDir(), "acl.hujson")
	require.NoError(t, os.WriteFile(path, []byte("{}\n"), 0o640))

	api := headscaleV1APIServer{h: createFileModeTestApp(t, path)}

	response, err := api.SetPolicy(context.Background(), &v1.SetPolicyRequest{Policy: fileModePolicy})
	require.NoError(t, err)
	assert.Equal(t, fileModePolicy, response.GetPolicy())
	assert.NotNil(t, response.GetUpdatedAt(), "file mode has no row to take a timestamp from")

	onDisk, err := os.ReadFile(path)
	require.NoError(t, err)
	assert.Equal(t, fileModePolicy, string(onDisk), "the file must hold exactly what was submitted")

	info, err := os.Stat(path)
	require.NoError(t, err)
	assert.Equal(t, os.FileMode(0o640), info.Mode().Perm(), "an existing file keeps its permissions")

	// No leftovers from the atomic write.
	entries, err := os.ReadDir(filepath.Dir(path))
	require.NoError(t, err)
	require.Len(t, entries, 1, "the temporary file must be renamed, not left behind")
}

// TestSetPolicyFileModeRejectsInvalidPolicy checks that a policy which does not
// pass validation never reaches the file. The bytes on disk are what headscale
// loads on its next start, so writing them would be writing a server that
// cannot boot.
func TestSetPolicyFileModeRejectsInvalidPolicy(t *testing.T) {
	t.Parallel()

	path := filepath.Join(t.TempDir(), "acl.hujson")
	require.NoError(t, os.WriteFile(path, []byte(fileModePolicy), 0o644))

	before, err := os.Stat(path)
	require.NoError(t, err)

	api := headscaleV1APIServer{h: createFileModeTestApp(t, path)}

	for _, tt := range []struct {
		name   string
		policy string
	}{
		{
			name:   "syntax error",
			policy: `{"acls": [`,
		},
		{
			name:   "undefined group",
			policy: `{"acls":[{"action":"accept","src":["group:nonexistent"],"dst":["*:*"]}]}`,
		},
	} {
		t.Run(tt.name, func(t *testing.T) {
			_, err := api.SetPolicy(context.Background(), &v1.SetPolicyRequest{Policy: tt.policy})
			require.Error(t, err)

			onDisk, err := os.ReadFile(path)
			require.NoError(t, err)
			assert.Equal(t, fileModePolicy, string(onDisk), "a rejected policy must not reach the file")

			after, err := os.Stat(path)
			require.NoError(t, err)
			assert.Equal(t, before.ModTime(), after.ModTime(), "the file must not be rewritten")
		})
	}
}

// TestSetPolicyFileModeWithoutPath checks the error when policy.mode is file
// but policy.path was never configured: there is nowhere to store the policy.
func TestSetPolicyFileModeWithoutPath(t *testing.T) {
	t.Parallel()

	api := headscaleV1APIServer{h: createFileModeTestApp(t, "")}

	_, err := api.SetPolicy(context.Background(), &v1.SetPolicyRequest{Policy: fileModePolicy})
	require.ErrorIs(t, err, types.ErrPolicyPathNotSet)
}

// TestSetPolicyDatabaseModeStoresInDatabase is the regression guard for the
// mode that was already supported.
func TestSetPolicyDatabaseModeStoresInDatabase(t *testing.T) {
	t.Parallel()

	api := headscaleV1APIServer{h: createTestApp(t)}

	response, err := api.SetPolicy(context.Background(), &v1.SetPolicyRequest{Policy: fileModePolicy})
	require.NoError(t, err)
	assert.Equal(t, fileModePolicy, response.GetPolicy())

	stored, err := api.h.state.GetPolicy()
	require.NoError(t, err)
	assert.Equal(t, fileModePolicy, stored.Data)
}
