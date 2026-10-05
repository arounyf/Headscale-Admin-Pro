package types

import (
	"errors"

	"gorm.io/gorm"
)

var (
	ErrPolicyNotFound         = errors.New("acl policy not found")
	ErrPolicyUpdateIsDisabled = errors.New("update is disabled for modes other than 'database'")
	ErrPolicyPathNotSet       = errors.New("policy.path is not set, cannot store the policy in file mode")
)

// Policy represents a policy in the database.
type Policy struct {
	gorm.Model

	// Data contains the policy in HuJSON format.
	Data string
}
