package v2

import (
	"net/netip"
	"testing"

	"github.com/juanfont/headscale/hscontrol/types"
	"github.com/stretchr/testify/require"
	"gorm.io/gorm"
	"tailscale.com/tailcfg"
)

// mkTenantNode 造一个归属 user 的节点，可选地广告并批准一条子网路由。
func mkTenantNode(id types.NodeID, name, ip, route string, user types.User) *types.Node {
	n := &types.Node{
		ID:       id,
		Hostname: name,
		IPv4:     ap(ip),
		User:     new(user),
		UserID:   new(user.ID),
		Hostinfo: &tailcfg.Hostinfo{},
	}

	if route != "" {
		p := netip.MustParsePrefix(route)
		n.Hostinfo.RoutableIPs = []netip.Prefix{p}
		n.ApprovedRoutes = []netip.Prefix{p}
	}

	return n
}

// TestNoCrossTenantPeerLeakOnOverlappingSubnet 守住两个租户宣告同一网段时的
// peer 可见性隔离。
//
// compileAutogroupSelf 会把本用户节点的 ApprovedRoutes 同时展开进规则的 src
// 和 dst，而 canAccess 只把网段按值比较、从不问它归谁；BuildPeerMap 的
// per-node 路径又是「四向任一可达即互为 peer」。两边网段一撞，对方的子网
// 路由器就会被写进本租户节点的 peer 列表，泄漏主机名、节点 IP 和 endpoints。
//
// 网段不重叠时本来就不泄漏（对照组），所以这条测试必须两种都覆盖：
// 断言的是「不管撞不撞车，a 租户的客户端都只看得见自己租户的路由器」。
func TestNoCrossTenantPeerLeakOnOverlappingSubnet(t *testing.T) {
	userA := types.User{Model: gorm.Model{ID: 1}, Name: "tenant-a", Email: "a@example.com"}
	userB := types.User{Model: gorm.Model{ID: 2}, Name: "tenant-b", Email: "b@example.com"}
	users := types.Users{userA, userB}

	// 面板 ACL 模版里的那条规则。
	policyStr := `{
		"acls": [
			{"action": "accept", "src": ["autogroup:member"], "dst": ["autogroup:self:*"]}
		]
	}`

	for _, tc := range []struct {
		name   string
		aRoute string
		bRoute string
	}{
		{name: "overlapping-10.99", aRoute: "10.99.0.0/24", bRoute: "10.99.0.0/24"},
		{name: "disjoint-control", aRoute: "10.99.0.0/24", bRoute: "10.88.0.0/24"},
	} {
		t.Run(tc.name, func(t *testing.T) {
			aClient := mkTenantNode(1, "a-client", "100.64.0.1", "", userA)
			aRouter := mkTenantNode(2, "a-router", "100.64.0.2", tc.aRoute, userA)
			bRouter := mkTenantNode(3, "b-router", "100.64.0.3", tc.bRoute, userB)
			nodes := types.Nodes{aClient, aRouter, bRouter}

			pm, err := NewPolicyManager([]byte(policyStr), users, nodes.ViewSlice())
			require.NoError(t, err)
			require.True(t, pm.needsPerNodeFilter, "autogroup:self 应走 per-node 路径")

			peers := pm.BuildPeerMap(nodes.ViewSlice())

			require.NotContains(t, peers[aClient.ID], bRouter.ID,
				"a-client 看见了别的租户的 b-router —— 跨租户 peer 泄漏")

			// 本租户的路由器始终要在，否则说明这道闸收得太紧。
			require.Contains(t, peers[aClient.ID], aRouter.ID,
				"a-client 应当看得见自己租户的 a-router")
		})
	}
}
