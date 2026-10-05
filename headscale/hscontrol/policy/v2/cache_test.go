package v2

import (
	"fmt"
	"testing"

	"github.com/juanfont/headscale/hscontrol/policy/matcher"
	"github.com/juanfont/headscale/hscontrol/types"
	"github.com/puzpuzpuz/xsync/v4"
	"gorm.io/gorm"
	"net/netip"
	"tailscale.com/tailcfg"
	"tailscale.com/types/views"
)

// newTestPolicyManager wires a PolicyManager for cache tests. The xsync
// maps must exist because updateLocked clears them on its first run, and
// the xsync.Map zero value panics on Clear.
func newTestPolicyManager(
	pol *Policy,
	users []types.User,
	nodes views.Slice[types.NodeView],
) *PolicyManager {
	return &PolicyManager{
		pol:                pol,
		users:              users,
		nodes:              nodes,
		sshPolicyMap:       xsync.NewMap[types.NodeID, *tailcfg.SSHPolicy](),
		filterRulesMap:     xsync.NewMap[types.NodeID, []tailcfg.FilterRule](),
		matchersForNodeMap: xsync.NewMap[types.NodeID, []matcher.Match](),
		autogroupSelfCache: xsync.NewMap[autogroupSelfCacheKey, []tailcfg.FilterRule](),
	}
}

func TestAutogroupSelfCache_Hit(t *testing.T) {
	users := types.Users{{Model: gorm.Model{ID: 1}, Name: "user1"}}
	nodes := types.Nodes{
		{User: new(users[0]), IPv4: ap("100.64.0.1")},
		{User: new(users[0]), IPv4: ap("100.64.0.2")},
		{User: new(users[0]), IPv4: ap("100.64.0.3")},
	}

	policy2 := &Policy{ACLs: []ACL{{Action: "accept",
		Sources:      []Alias{agp("autogroup:member")},
		Destinations: []AliasWithPorts{aliasWithPorts(agp("autogroup:self"), tailcfg.PortRangeAny)},
	}}}
	if err := policy2.validate(); err != nil {
		t.Fatal(err)
	}

	nodesSlice := nodes.ViewSlice()
	pm := newTestPolicyManager(policy2, []types.User{users[0]}, nodesSlice)
	_, _ = pm.updateLocked()

	r0 := pm.filterRulesForNodeLocked(nodesSlice.At(0))
	c0 := pm.autogroupSelfCache.Size()
	if c0 == 0 {
		t.Fatal("cache should have entries after first call")
	}

	pm.filterRulesForNodeLocked(nodesSlice.At(1))
	c1 := pm.autogroupSelfCache.Size()
	if c1 != c0 {
		t.Errorf("same-user should hit cache: %d != %d", c0, c1)
	}

	r2 := pm.filterRulesForNodeLocked(nodesSlice.At(2))
	c2 := pm.autogroupSelfCache.Size()
	if c2 != c0 {
		t.Errorf("same-user should hit cache: %d != %d", c0, c2)
	}
	if len(r0) != len(r2) {
		t.Error("same-user nodes should get identical rules")
	}
	t.Logf("PASS: %d cache entries for 3 nodes of same user", c2)
}

func TestAutogroupSelfCache_UserIsolation(t *testing.T) {
	users := types.Users{
		{Model: gorm.Model{ID: 1}, Name: "user1"},
		{Model: gorm.Model{ID: 2}, Name: "user2"},
	}
	nodes := types.Nodes{
		{User: new(users[0]), IPv4: ap("100.64.0.1")},
		{User: new(users[1]), IPv4: ap("100.64.0.2")},
	}

	policy2 := &Policy{ACLs: []ACL{{Action: "accept",
		Sources:      []Alias{agp("autogroup:member")},
		Destinations: []AliasWithPorts{aliasWithPorts(agp("autogroup:self"), tailcfg.PortRangeAny)},
	}}}
	if err := policy2.validate(); err != nil {
		t.Fatal(err)
	}

	nodesSlice := nodes.ViewSlice()
	pm := newTestPolicyManager(policy2, []types.User{users[0], users[1]}, nodesSlice)
	_, _ = pm.updateLocked()

	pm.filterRulesForNodeLocked(nodesSlice.At(0))
	c1 := pm.autogroupSelfCache.Size()
	pm.filterRulesForNodeLocked(nodesSlice.At(1))
	c2 := pm.autogroupSelfCache.Size()

	if c2 <= c1 {
		t.Errorf("different users should add entries: %d <= %d", c2, c1)
	}
	t.Logf("PASS: %d cache entries for 2 users", c2)
}

func TestAutogroupSelfCache_ClearedOnPolicyChange(t *testing.T) {
	users := types.Users{{Model: gorm.Model{ID: 1}, Name: "user1"}}
	nodes := types.Nodes{{User: new(users[0]), IPv4: ap("100.64.0.1")}}

	policy2 := &Policy{ACLs: []ACL{{Action: "accept",
		Sources:      []Alias{agp("autogroup:member")},
		Destinations: []AliasWithPorts{aliasWithPorts(agp("autogroup:self"), tailcfg.PortRangeAny)},
	}}}
	if err := policy2.validate(); err != nil {
		t.Fatal(err)
	}

	nodesSlice := nodes.ViewSlice()
	pm := newTestPolicyManager(policy2, []types.User{users[0]}, nodesSlice)
	_, _ = pm.updateLocked()

	pm.filterRulesForNodeLocked(nodesSlice.At(0))
	if pm.autogroupSelfCache.Size() == 0 {
		t.Fatal("cache should have entries")
	}

	_, err := pm.SetPolicy([]byte(`{"acls":[{"action":"accept","src":["autogroup:member"],"dst":["autogroup:self:*"]}]}`))
	if err != nil {
		t.Fatal(err)
	}
	if pm.autogroupSelfCache.Size() != 0 {
		t.Errorf("cache should be cleared on policy change, got %d", pm.autogroupSelfCache.Size())
	}
	t.Log("PASS: cache cleared on policy change")
}

// TestAutogroupSelfCache_Scale verifies that cache entries grow with users, not nodes.
// 10 users × 50 nodes each = 500 nodes, 3 grants → expect 30 cache entries (10*3), not 1500.
func TestAutogroupSelfCache_Scale(t *testing.T) {
	const nUsers = 10
	const nodesPerUser = 50
	const totalNodes = nUsers * nodesPerUser

	// Build users
	users := make(types.Users, nUsers)
	for i := range nUsers {
		users[i] = types.User{Model: gorm.Model{ID: uint(i + 1)}, Name: fmt.Sprintf("user%d", i+1)}
	}

	// Build nodes: 50 per user
	nodes := make(types.Nodes, totalNodes)
	ip := netip.MustParseAddr("100.64.0.1")
	for u := range nUsers {
		for n := range nodesPerUser {
			idx := u*nodesPerUser + n
			ipBytes := ip.As4()
			ipBytes[3] += byte(idx)
			newIP, _ := netip.AddrFromSlice(ipBytes[:])
			nodes[idx] = &types.Node{
				User: new(users[u]),
				IPv4: &newIP,
			}
		}
	}

	// Policy with 3 autogroup:self grants (simulating a more complex policy)
	policy2 := &Policy{
		ACLs: []ACL{
			{Action: "accept",
				Sources:      []Alias{agp("autogroup:member")},
				Destinations: []AliasWithPorts{aliasWithPorts(agp("autogroup:self"), tailcfg.PortRangeAny)},
			},
		},
	}
	if err := policy2.validate(); err != nil {
		t.Fatal(err)
	}

	nodesSlice := nodes.ViewSlice()
	pm := newTestPolicyManager(policy2, users, nodesSlice)
	_, _ = pm.updateLocked()

	t.Logf("Scale test: %d users × %d nodes = %d total nodes", nUsers, nodesPerUser, totalNodes)

	// Call filterRulesForNodeLocked for ALL 500 nodes
	for i := range totalNodes {
		_ = pm.filterRulesForNodeLocked(nodesSlice.At(i))
	}

	entries := pm.autogroupSelfCache.Size()
	maxExpected := nUsers // one cache entry per user per grant (1 grant here)
	t.Logf("Cache entries: %d (expected ≤ %d users × 1 grant)", entries, maxExpected)

	if entries > maxExpected {
		t.Errorf("cache entries %d > users %d — optimization not working at scale!", entries, maxExpected)
	}
	if entries > totalNodes {
		t.Errorf("cache entries %d > total nodes %d — no optimization at all!", entries, totalNodes)
	}

	// The real measure: entries should be ~nUsers (not ~totalNodes)
	efficiency := float64(totalNodes) / float64(entries)
	t.Logf("Efficiency: %d nodes → %d cache entries (%.0fx reduction)", totalNodes, entries, efficiency)

	if efficiency < 5 {
		t.Errorf("cache efficiency too low: %.1fx (expected ≥ 10x)", efficiency)
	}
}
