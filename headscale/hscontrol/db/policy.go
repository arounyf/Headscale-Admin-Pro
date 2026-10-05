package db

import (
	"errors"
	"fmt"
	"os"
	"path/filepath"

	"github.com/juanfont/headscale/hscontrol/types"
	"github.com/juanfont/headscale/hscontrol/util"
	"gorm.io/gorm"
	"gorm.io/gorm/clause"
)

// defaultPolicyFileMode is used when the policy file does not exist yet.
// An existing file keeps its own permissions, see [writePolicyFile].
const defaultPolicyFileMode = 0o644

// SetPolicy sets the policy in the database.
func (hsdb *HSDatabase) SetPolicy(policy string) (*types.Policy, error) {
	// Create a new policy.
	p := types.Policy{
		Data: policy,
	}

	err := hsdb.DB.Clauses(clause.Returning{}).Create(&p).Error
	if err != nil {
		return nil, err
	}

	return &p, nil
}

// GetPolicy returns the latest policy in the database.
func (hsdb *HSDatabase) GetPolicy() (*types.Policy, error) {
	return GetPolicy(hsdb.DB)
}

// GetPolicy returns the latest policy from the database.
// This standalone function can be used in contexts where [HSDatabase] is not available,
// such as during migrations.
func GetPolicy(tx *gorm.DB) (*types.Policy, error) {
	var p types.Policy

	// Query:
	// SELECT * FROM policies ORDER BY id DESC LIMIT 1;
	err := tx.
		Order("id DESC").
		Limit(1).
		First(&p).Error
	if err != nil {
		if errors.Is(err, gorm.ErrRecordNotFound) {
			return nil, types.ErrPolicyNotFound
		}

		return nil, err
	}

	return &p, nil
}

// PolicyBytes loads policy configuration from file or database based on the configured mode.
// Returns nil if no policy is configured, which is valid.
// This standalone function can be used in contexts where [HSDatabase] is not available,
// such as during migrations.
func PolicyBytes(tx *gorm.DB, cfg *types.Config) ([]byte, error) {
	switch cfg.Policy.Mode {
	case types.PolicyModeFile:
		path := cfg.Policy.Path

		// It is fine to start headscale without a policy file.
		if len(path) == 0 {
			return nil, nil
		}

		absPath := util.AbsolutePathFromConfigPath(path)

		return os.ReadFile(absPath)

	case types.PolicyModeDB:
		p, err := GetPolicy(tx)
		if err != nil {
			if errors.Is(err, types.ErrPolicyNotFound) {
				return nil, nil
			}

			return nil, err
		}

		if p.Data == "" {
			return nil, nil
		}

		return []byte(p.Data), nil
	}

	return nil, nil
}

// SetPolicyBytes stores the policy in the location selected by cfg.Policy.Mode:
// a row in the database, or the file referenced by policy.path.
//
// The caller must validate the policy before calling this. In file mode the
// bytes written here are what headscale loads on its next start, so storing a
// policy that does not parse would leave the server unable to boot.
func (hsdb *HSDatabase) SetPolicyBytes(cfg *types.Config, data string) error {
	switch cfg.Policy.Mode {
	case types.PolicyModeFile:
		if cfg.Policy.Path == "" {
			return types.ErrPolicyPathNotSet
		}

		return writePolicyFile(util.AbsolutePathFromConfigPath(cfg.Policy.Path), data)

	case types.PolicyModeDB:
		_, err := hsdb.SetPolicy(data)

		return err
	}

	return fmt.Errorf("unsupported policy.mode: %q", cfg.Policy.Mode)
}

// writePolicyFile replaces path with data atomically: the data goes to a
// temporary file in the same directory, which is then renamed over the target.
// A partial write (full disk, crash) therefore never leaves a truncated policy
// behind for the next start to fail on.
func writePolicyFile(path, data string) error {
	dir := filepath.Dir(path)

	err := util.EnsureDir(dir)
	if err != nil {
		return fmt.Errorf("creating policy directory: %w", err)
	}

	// Keep the permissions of an existing policy file. os.CreateTemp would
	// otherwise narrow them to 0600, locking out every reader that is not the
	// headscale user.
	mode := os.FileMode(defaultPolicyFileMode)

	info, err := os.Stat(path)
	if err == nil {
		mode = info.Mode().Perm()
	}

	tmp, err := os.CreateTemp(dir, filepath.Base(path)+".*.tmp")
	if err != nil {
		return fmt.Errorf("creating temporary policy file: %w", err)
	}

	tmpName := tmp.Name()

	cleanup := func() {
		_ = os.Remove(tmpName)
	}

	_, err = tmp.WriteString(data)
	if err != nil {
		_ = tmp.Close()

		cleanup()

		return fmt.Errorf("writing policy file: %w", err)
	}

	err = tmp.Chmod(mode)
	if err != nil {
		_ = tmp.Close()

		cleanup()

		return fmt.Errorf("setting policy file permissions: %w", err)
	}

	err = tmp.Close()
	if err != nil {
		cleanup()

		return fmt.Errorf("closing policy file: %w", err)
	}

	err = os.Rename(tmpName, path)
	if err != nil {
		cleanup()

		return fmt.Errorf("replacing policy file: %w", err)
	}

	return nil
}
