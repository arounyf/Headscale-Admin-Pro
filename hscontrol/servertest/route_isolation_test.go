package servertest_test

import (
	"context"
	"net/netip"
	"slices"
	"testing"
	"time"

	"github.com/juanfont/headscale/hscontrol/policy/matcher"
	"github.com/juanfont/headscale/hscontrol/servertest"
	"github.com/juanfont/headscale/hscontrol/types"
	"github.com/stretchr/testify/require"
	"tailscale.com/tailcfg"
)

const routeIsoTimeout = 15 * time.Second

// TestMultiTenantRouteIsolation verifies the core multi-tenant guarantee:
// user A's nodes cannot see subnet routes from user B's routers, and
// vice versa. Routes are scoped per-user via per-user primary routes.
func TestMultiTenantRouteIsolation(t *testing.T) {
	srv := servertest.NewServer(t)

	// ── Users ──
	userA := srv.CreateUser(t, "tenant-a")
	userB := srv.CreateUser(t, "tenant-b")

	// ── User A: one router + one regular node ──
	aRouter := servertest.NewClient(t, srv, "a-router", servertest.WithUser(userA))
	aNode := servertest.NewClient(t, srv, "a-node", servertest.WithUser(userA))

	// ── User B: one router + one regular node ──
	bRouter := servertest.NewClient(t, srv, "b-router", servertest.WithUser(userB))
	bNode := servertest.NewClient(t, srv, "b-node", servertest.WithUser(userB))

	// Wait for full mesh
	aRouter.WaitForPeers(t, 3, routeIsoTimeout)
	aNode.WaitForPeers(t, 3, routeIsoTimeout)
	bRouter.WaitForPeers(t, 3, routeIsoTimeout)
	bNode.WaitForPeers(t, 3, routeIsoTimeout)

	// ── Advertise and approve routes ──
	routeA := netip.MustParsePrefix("10.42.0.0/24")
	routeB := netip.MustParsePrefix("10.43.0.0/24")

	advertiseAndApproveRoute(t, srv, aRouter, routeA)
	advertiseAndApproveRoute(t, srv, bRouter, routeB)

	// ── Server-side checks: RoutesForPeer ──

	aRouterID := findNodeID(t, srv, "a-router")
	aNodeID := findNodeID(t, srv, "a-node")
	bRouterID := findNodeID(t, srv, "b-router")
	bNodeID := findNodeID(t, srv, "b-node")

	aRouterView, _ := srv.State().GetNodeByID(aRouterID)
	aNodeView, _ := srv.State().GetNodeByID(aNodeID)
	bRouterView, _ := srv.State().GetNodeByID(bRouterID)
	bNodeView, _ := srv.State().GetNodeByID(bNodeID)

	// Get real matchers from the policy engine (default DB mode allows all)
	aNodeMatchers, _ := srv.State().MatchersForNode(aNodeView)
	bNodeMatchers, _ := srv.State().MatchersForNode(bNodeView)

	t.Run("same-user sees own routes", func(t *testing.T) {
		// a-node looking at a-router: should see 10.42.0.0/24
		routes := srv.State().RoutesForPeer(aNodeView, aRouterView, aNodeMatchers)
		require.True(t, slices.Contains(routes, routeA),
			"a-node should see a-router's route %s, got %v", routeA, routes)

		// b-node looking at b-router: should see 10.43.0.0/24
		routes = srv.State().RoutesForPeer(bNodeView, bRouterView, bNodeMatchers)
		require.True(t, slices.Contains(routes, routeB),
			"b-node should see b-router's route %s, got %v", routeB, routes)
	})

	t.Run("cross-user route isolation", func(t *testing.T) {
		// a-node looking at b-router: should NOT see 10.43.0.0/24
		routes := srv.State().RoutesForPeer(aNodeView, bRouterView, aNodeMatchers)
		require.False(t, slices.Contains(routes, routeB),
			"a-node should NOT see b-router's route %s (cross-tenant leak!), got %v", routeB, routes)

		// b-node looking at a-router: should NOT see 10.42.0.0/24
		routes = srv.State().RoutesForPeer(bNodeView, aRouterView, bNodeMatchers)
		require.False(t, slices.Contains(routes, routeA),
			"b-node should NOT see a-router's route %s (cross-tenant leak!), got %v", routeA, routes)
	})

	// Note: client-side netmap verification is covered by existing
	// integration tests. Server-side RoutesForPeer checks above
	// directly validate the multi-tenant route isolation boundary.
}

// TestPerUserPrimaryRoutes_HAFailover verifies that HA failover operates
// within a user scope: when the primary for a prefix goes offline, a
// second router from the SAME user takes over.
func TestPerUserPrimaryRoutes_HAFailover(t *testing.T) {
	srv := servertest.NewServer(t)
	user := srv.CreateUser(t, "tenant")

	r1 := servertest.NewClient(t, srv, "r1", servertest.WithUser(user))
	r2 := servertest.NewClient(t, srv, "r2", servertest.WithUser(user))

	r1.WaitForPeers(t, 1, routeIsoTimeout)
	r2.WaitForPeers(t, 1, routeIsoTimeout)

	route := netip.MustParsePrefix("10.99.0.0/24")
	r1ID := advertiseAndApproveRoute(t, srv, r1, route)
	r2ID := advertiseAndApproveRoute(t, srv, r2, route)

	// Low-ID wins primary
	primaries := srv.State().GetNodePrimaryRoutes(r1ID)
	require.True(t, slices.Contains(primaries, route),
		"r1 (lower ID) should be primary for %s, got %v", route, primaries)

	r2Primaries := srv.State().GetNodePrimaryRoutes(r2ID)
	require.False(t, slices.Contains(r2Primaries, route),
		"r2 should NOT be primary while r1 is healthy")

	// Take r1 offline
	r1.Disconnect(t)

	// Wait for r2 to become primary (poll until election runs)
	require.Eventually(t, func() bool {
		p := srv.State().GetNodePrimaryRoutes(r2ID)
		return slices.Contains(p, route)
	}, routeIsoTimeout, 200*time.Millisecond,
		"r2 should become primary after r1 disconnects")

	r1Primaries := srv.State().GetNodePrimaryRoutes(r1ID)
	require.False(t, slices.Contains(r1Primaries, route),
		"offline r1 should no longer be primary")
}

// TestSameRouteCrossUser verifies that when two users each advertise the
// SAME route prefix, each user's nodes can only see their own user's route
// and primary election operates independently within each user scope.
func TestSameRouteCrossUser(t *testing.T) {
	srv := servertest.NewServer(t)

	userA := srv.CreateUser(t, "tenant-a")
	userB := srv.CreateUser(t, "tenant-b")

	// User A: two routers advertising same prefix (HA pair)
	aR1 := servertest.NewClient(t, srv, "a-r1", servertest.WithUser(userA))
	aR2 := servertest.NewClient(t, srv, "a-r2", servertest.WithUser(userA))
	// User A: one regular node
	aNode := servertest.NewClient(t, srv, "a-node", servertest.WithUser(userA))

	// User B: one router advertising same prefix as A
	bR1 := servertest.NewClient(t, srv, "b-r1", servertest.WithUser(userB))
	// User B: one regular node
	bNode := servertest.NewClient(t, srv, "b-node", servertest.WithUser(userB))

	aR1.WaitForPeers(t, 4, routeIsoTimeout)
	aR2.WaitForPeers(t, 4, routeIsoTimeout)
	aNode.WaitForPeers(t, 4, routeIsoTimeout)
	bR1.WaitForPeers(t, 4, routeIsoTimeout)
	bNode.WaitForPeers(t, 4, routeIsoTimeout)

	// All advertise the SAME route prefix
	sameRoute := netip.MustParsePrefix("10.42.0.0/24")
	advertiseAndApproveRoute(t, srv, aR1, sameRoute)
	advertiseAndApproveRoute(t, srv, aR2, sameRoute)
	advertiseAndApproveRoute(t, srv, bR1, sameRoute)

	aNodeID := findNodeID(t, srv, "a-node")
	bNodeID := findNodeID(t, srv, "b-node")
	aR1ID := findNodeID(t, srv, "a-r1")
	aR2ID := findNodeID(t, srv, "a-r2")
	bR1ID := findNodeID(t, srv, "b-r1")

	aNodeView, _ := srv.State().GetNodeByID(aNodeID)
	bNodeView, _ := srv.State().GetNodeByID(bNodeID)
	aR1View, _ := srv.State().GetNodeByID(aR1ID)
	aR2View, _ := srv.State().GetNodeByID(aR2ID)
	bR1View, _ := srv.State().GetNodeByID(bR1ID)

	aMatchers, _ := srv.State().MatchersForNode(aNodeView)
	bMatchers, _ := srv.State().MatchersForNode(bNodeView)

	t.Run("same-user sees primary routes", func(t *testing.T) {
		// a-node sees 10.42.0.0/24 from a-r1 (a-r1 is primary)
		routes := srv.State().RoutesForPeer(aNodeView, aR1View, aMatchers)
		require.True(t, slices.Contains(routes, sameRoute),
			"a-node should see a-r1's route %s, got %v", sameRoute, routes)

		// a-node does NOT see 10.42.0.0/24 from a-r2 (not primary, a-r1 is)
		routes = srv.State().RoutesForPeer(aNodeView, aR2View, aMatchers)
		require.False(t, slices.Contains(routes, sameRoute),
			"a-node should NOT see a-r2's route (a-r1 is primary), got %v", routes)

		// b-node sees 10.42.0.0/24 from b-r1 (b-r1 is primary in tenant-b)
		routes = srv.State().RoutesForPeer(bNodeView, bR1View, bMatchers)
		require.True(t, slices.Contains(routes, sameRoute),
			"b-node should see b-r1's route %s, got %v", sameRoute, routes)
	})

	t.Run("cross-user same-route isolated", func(t *testing.T) {
		// a-node looking at b-r1: should NOT see b-r1's 10.42.0.0/24
		routes := srv.State().RoutesForPeer(aNodeView, bR1View, aMatchers)
		require.False(t, slices.Contains(routes, sameRoute),
			"a-node should NOT see b-r1's route (cross-tenant leak!), got %v", routes)

		// b-node looking at a-r1: should NOT see a-r1's 10.42.0.0/24
		routes = srv.State().RoutesForPeer(bNodeView, aR1View, bMatchers)
		require.False(t, slices.Contains(routes, sameRoute),
			"b-node should NOT see a-r1's route (cross-tenant leak!), got %v", routes)

		// b-node looking at a-r2: should NOT see a-r2's 10.42.0.0/24
		routes = srv.State().RoutesForPeer(bNodeView, aR2View, bMatchers)
		require.False(t, slices.Contains(routes, sameRoute),
			"b-node should NOT see a-r2's route (cross-tenant leak!), got %v", routes)

		// The checks above all use viewers that advertise nothing. A viewer
		// that advertises the same prefix takes the co-router visibility
		// branch, which is where multi-tenant isolation is easiest to lose:
		// that branch exists so HA secondaries can learn which peer is
		// primary for a prefix they share, and it must still refuse a peer
		// from another scope.
		aR1Matchers, _ := srv.State().MatchersForNode(aR1View)
		aR2Matchers, _ := srv.State().MatchersForNode(aR2View)

		// a-r1 is tenant-a's primary and advertises the prefix itself.
		routes = srv.State().RoutesForPeer(aR1View, bR1View, aR1Matchers)
		require.False(t, slices.Contains(routes, sameRoute),
			"a-r1 (a router) should NOT see b-r1's route (cross-tenant leak!), got %v", routes)

		// a-r2 is tenant-a's secondary and also advertises the prefix.
		routes = srv.State().RoutesForPeer(aR2View, bR1View, aR2Matchers)
		require.False(t, slices.Contains(routes, sameRoute),
			"a-r2 (a router) should NOT see b-r1's route (cross-tenant leak!), got %v", routes)
	})

	t.Run("per-user primary election independent", func(t *testing.T) {
		// Within user A, the lower-ID router should be primary
		aPrimaries := srv.State().GetNodePrimaryRoutes(aR1ID)
		require.True(t, slices.Contains(aPrimaries, sameRoute),
			"a-r1 (lower ID) should be primary for %s in tenant-a, got %v", sameRoute, aPrimaries)

		aR2Primaries := srv.State().GetNodePrimaryRoutes(aR2ID)
		require.False(t, slices.Contains(aR2Primaries, sameRoute),
			"a-r2 should NOT be primary while a-r1 is healthy")

		// Within user B, b-r1 is the only router so it should be primary
		bPrimaries := srv.State().GetNodePrimaryRoutes(bR1ID)
		require.True(t, slices.Contains(bPrimaries, sameRoute),
			"b-r1 should be primary for %s in tenant-b, got %v", sameRoute, bPrimaries)
	})
}

// routeOwners returns the netmap peers that the client is told are the
// primary owner of prefix p. A peer shows up here only when
// [State.RoutesForPeer] returned p for this exact (viewer, peer) pair, so
// the result is what the client would actually install as a route.
func routeOwners(c *servertest.TestClient, p netip.Prefix) []string {
	nm := c.Netmap()
	if nm == nil {
		return nil
	}

	var owners []string

	for _, peer := range nm.Peers {
		routes := peer.PrimaryRoutes()

		for i := range routes.Len() {
			if routes.At(i) == p {
				if hi := peer.Hostinfo(); hi.Valid() {
					owners = append(owners, hi.Hostname())
				}

				break
			}
		}
	}

	slices.Sort(owners)

	return owners
}

// TestThreeUsersSameRoute is the three-tenant case: users a, b and c each
// advertise the SAME prefix, and every tenant must keep routing through
// its own router. This is the scenario an operator hits when several
// customers happen to use 192.168.1.0/24 behind their own router.
//
// It asserts on the server-side route table and on the netmap each client
// actually received — [tailcfg.Node.PrimaryRoutes] is built per viewer
// from [State.RoutesForPeer], so a leak appears as a foreign router being
// presented to a tenant as an owner of that prefix.
func TestThreeUsersSameRoute(t *testing.T) {
	srv := servertest.NewServer(t)

	userA := srv.CreateUser(t, "tenant-a")
	userB := srv.CreateUser(t, "tenant-b")
	userC := srv.CreateUser(t, "tenant-c")

	route := netip.MustParsePrefix("192.168.1.0/24")

	aRouter := servertest.NewClient(t, srv, "a-router", servertest.WithUser(userA))
	aNode := servertest.NewClient(t, srv, "a-node", servertest.WithUser(userA))
	bRouter := servertest.NewClient(t, srv, "b-router", servertest.WithUser(userB))
	bNode := servertest.NewClient(t, srv, "b-node", servertest.WithUser(userB))
	cRouter := servertest.NewClient(t, srv, "c-router", servertest.WithUser(userC))
	cNode := servertest.NewClient(t, srv, "c-node", servertest.WithUser(userC))

	clients := []*servertest.TestClient{aRouter, aNode, bRouter, bNode, cRouter, cNode}
	for _, c := range clients {
		c.WaitForPeers(t, len(clients)-1, routeIsoTimeout)
	}

	advertiseAndApproveRoute(t, srv, aRouter, route)
	advertiseAndApproveRoute(t, srv, bRouter, route)
	advertiseAndApproveRoute(t, srv, cRouter, route)

	aRouterID := findNodeID(t, srv, "a-router")
	aNodeID := findNodeID(t, srv, "a-node")
	bRouterID := findNodeID(t, srv, "b-router")
	bNodeID := findNodeID(t, srv, "b-node")
	cRouterID := findNodeID(t, srv, "c-router")
	cNodeID := findNodeID(t, srv, "c-node")

	aRouterView, _ := srv.State().GetNodeByID(aRouterID)
	aNodeView, _ := srv.State().GetNodeByID(aNodeID)
	bRouterView, _ := srv.State().GetNodeByID(bRouterID)
	bNodeView, _ := srv.State().GetNodeByID(bNodeID)
	cRouterView, _ := srv.State().GetNodeByID(cRouterID)
	cNodeView, _ := srv.State().GetNodeByID(cNodeID)

	aNodeMatchers, _ := srv.State().MatchersForNode(aNodeView)
	bNodeMatchers, _ := srv.State().MatchersForNode(bNodeView)
	cNodeMatchers, _ := srv.State().MatchersForNode(cNodeView)
	aRouterMatchers, _ := srv.State().MatchersForNode(aRouterView)
	bRouterMatchers, _ := srv.State().MatchersForNode(bRouterView)
	cRouterMatchers, _ := srv.State().MatchersForNode(cRouterView)

	t.Run("每个租户各自选出 primary", func(t *testing.T) {
		// All three are primary — in their own scope. The election is
		// keyed by types.UserID, so one prefix has three winners.
		require.True(t, slices.Contains(srv.State().GetNodePrimaryRoutes(aRouterID), route),
			"a-router 应在 tenant-a 内成为 %s 的 primary", route)
		require.True(t, slices.Contains(srv.State().GetNodePrimaryRoutes(bRouterID), route),
			"b-router 应在 tenant-b 内成为 %s 的 primary", route)
		require.True(t, slices.Contains(srv.State().GetNodePrimaryRoutes(cRouterID), route),
			"c-router 应在 tenant-c 内成为 %s 的 primary", route)
	})

	t.Run("普通节点只看见自己租户的路由", func(t *testing.T) {
		own := map[string]struct {
			view     types.NodeView
			router   types.NodeView
			matchers []matcher.Match
		}{
			"a-node": {aNodeView, aRouterView, aNodeMatchers},
			"b-node": {bNodeView, bRouterView, bNodeMatchers},
			"c-node": {cNodeView, cRouterView, cNodeMatchers},
		}

		for name, tc := range own {
			routes := srv.State().RoutesForPeer(tc.view, tc.router, tc.matchers)
			require.True(t, slices.Contains(routes, route),
				"%s 应看见自己租户 router 的 %s，实际 %v", name, route, routes)
		}
	})

	t.Run("跨租户不可见", func(t *testing.T) {
		// Every (viewer, foreign router) pair. Each viewer advertises
		// nothing, so this exercises the plain route table path.
		type pair struct {
			viewer, peer types.NodeView
			matchers     []matcher.Match
		}

		pairs := []pair{
			{aNodeView, bRouterView, aNodeMatchers},
			{aNodeView, cRouterView, aNodeMatchers},
			{bNodeView, aRouterView, bNodeMatchers},
			{bNodeView, cRouterView, bNodeMatchers},
			{cNodeView, aRouterView, cNodeMatchers},
			{cNodeView, bRouterView, cNodeMatchers},
		}

		for _, p := range pairs {
			routes := srv.State().RoutesForPeer(p.viewer, p.peer, p.matchers)
			require.False(t, slices.Contains(routes, route),
				"跨租户泄漏：%s 看见了 %s 的 %s，实际 %v",
				p.viewer.Hostname(), p.peer.Hostname(), route, routes)
		}
	})

	t.Run("router 视角也不可跨租户", func(t *testing.T) {
		// A viewer that advertises the prefix itself takes the co-router
		// visibility branch — the path that exists so HA secondaries can
		// learn the primary, and the easiest place to lose isolation.
		type pair struct {
			viewer, peer types.NodeView
			matchers     []matcher.Match
		}

		pairs := []pair{
			{aRouterView, bRouterView, aRouterMatchers},
			{aRouterView, cRouterView, aRouterMatchers},
			{bRouterView, aRouterView, bRouterMatchers},
			{bRouterView, cRouterView, bRouterMatchers},
			{cRouterView, aRouterView, cRouterMatchers},
			{cRouterView, bRouterView, cRouterMatchers},
		}

		for _, p := range pairs {
			routes := srv.State().RoutesForPeer(p.viewer, p.peer, p.matchers)
			require.False(t, slices.Contains(routes, route),
				"router 视角跨租户泄漏：%s 看见了 %s 的 %s，实际 %v",
				p.viewer.Hostname(), p.peer.Hostname(), route, routes)
		}
	})

	t.Run("netmap 端到端：各走各的", func(t *testing.T) {
		// The server-side table can be right while the wire is wrong, so
		// assert on what each client was actually handed. A router's own
		// netmap must list NO peer as owner of the prefix — it holds that
		// route locally — and each plain node must list exactly its own
		// tenant's router.
		want := map[*servertest.TestClient][]string{
			aRouter: nil,
			bRouter: nil,
			cRouter: nil,
			aNode:   {"a-router"},
			bNode:   {"b-router"},
			cNode:   {"c-router"},
		}

		for client, owners := range want {
			require.Eventually(t, func() bool {
				return slices.Equal(routeOwners(client, route), owners)
			}, routeIsoTimeout, 200*time.Millisecond,
				"%s 的 netmap 中 %s 的 owner 应是 %v，实际 %v（peers: %v）",
				client.Name, route, owners, routeOwners(client, route), client.PeerNames())
		}
	})
}

// TestPerUserPrimaryRoutes_ExitRouteUnaffected verifies that exit routes
// (0.0.0.0/0, ::/0) are excluded from primary election regardless of
// per-user scoping — they are not subject to HA failover.
func TestPerUserPrimaryRoutes_ExitRouteUnaffected(t *testing.T) {
	srv := servertest.NewServer(t)
	user := srv.CreateUser(t, "tenant")

	c := servertest.NewClient(t, srv, "exit-router", servertest.WithUser(user))
	c.WaitForPeers(t, 0, routeIsoTimeout)

	exitV4 := netip.MustParsePrefix("0.0.0.0/0")
	exitV6 := netip.MustParsePrefix("::/0")

	c.Direct().SetHostinfo(&tailcfg.Hostinfo{
		BackendLogID: "servertest-exit",
		Hostname:     "exit-router",
		RoutableIPs:  []netip.Prefix{exitV4, exitV6},
	})
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	_ = c.Direct().SendUpdate(ctx)

	nodeID := findNodeID(t, srv, "exit-router")

	// Approve both exit routes
	_, rc, err := srv.State().SetApprovedRoutes(nodeID, []netip.Prefix{exitV4, exitV6})
	require.NoError(t, err)
	srv.App.Change(rc)

	// Exit routes should NOT appear in primary routes
	primaries := srv.State().GetNodePrimaryRoutes(nodeID)
	require.False(t, slices.Contains(primaries, exitV4),
		"0.0.0.0/0 should not be elected as primary route")
	require.False(t, slices.Contains(primaries, exitV6),
		"::/0 should not be elected as primary route")
}

// ── 边界场景 ──

// TestUnapprovedRouteNotVisible verifies that a route is not visible to
// anyone until it has been approved via SetApprovedRoutes.
func TestUnapprovedRouteNotVisible(t *testing.T) {
	srv := servertest.NewServer(t)
	user := srv.CreateUser(t, "tenant")

	router := servertest.NewClient(t, srv, "router", servertest.WithUser(user))
	viewer := servertest.NewClient(t, srv, "viewer", servertest.WithUser(user))

	router.WaitForPeers(t, 1, routeIsoTimeout)
	viewer.WaitForPeers(t, 1, routeIsoTimeout)

	route := netip.MustParsePrefix("10.99.0.0/24")

	// Advertise but do NOT approve
	router.Direct().SetHostinfo(&tailcfg.Hostinfo{
		BackendLogID: "servertest-r",
		Hostname:     "router",
		RoutableIPs:  []netip.Prefix{route},
	})
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	_ = router.Direct().SendUpdate(ctx)

	routerID := findNodeID(t, srv, "router")
	viewerID := findNodeID(t, srv, "viewer")
	routerView, _ := srv.State().GetNodeByID(routerID)
	viewerView, _ := srv.State().GetNodeByID(viewerID)
	m, _ := srv.State().MatchersForNode(viewerView)

	routes := srv.State().RoutesForPeer(viewerView, routerView, m)
	require.False(t, slices.Contains(routes, route),
		"unapproved route should NOT be visible, got %v", routes)

	// Primary routes also shouldn't include unapproved
	primaries := srv.State().GetNodePrimaryRoutes(routerID)
	require.False(t, slices.Contains(primaries, route),
		"unapproved route should not be primary, got %v", primaries)
}

// TestMultipleRoutesPerUser verifies a user can have multiple distinct
// routes, all visible to their own nodes and isolated from other users.
func TestMultipleRoutesPerUser(t *testing.T) {
	srv := servertest.NewServer(t)

	userA := srv.CreateUser(t, "tenant-a")
	userB := srv.CreateUser(t, "tenant-b")

	aRouter := servertest.NewClient(t, srv, "a-router", servertest.WithUser(userA))
	aNode := servertest.NewClient(t, srv, "a-node", servertest.WithUser(userA))
	bRouter := servertest.NewClient(t, srv, "b-router", servertest.WithUser(userB))

	aRouter.WaitForPeers(t, 2, routeIsoTimeout)
	aNode.WaitForPeers(t, 2, routeIsoTimeout)
	bRouter.WaitForPeers(t, 2, routeIsoTimeout)

	r1 := netip.MustParsePrefix("10.10.0.0/24")
	r2 := netip.MustParsePrefix("10.20.0.0/24")
	r3 := netip.MustParsePrefix("192.168.0.0/16")

	// A advertises r1+r2, B advertises r3. A's two routes go in a single
	// call: the helper replaces the advertised and approved sets, so a
	// second call for the same router would drop r1 from both.
	advertiseAndApproveRoute(t, srv, aRouter, r1, r2)
	advertiseAndApproveRoute(t, srv, bRouter, r3)

	aNodeID := findNodeID(t, srv, "a-node")
	aRouterID := findNodeID(t, srv, "a-router")
	bRouterID := findNodeID(t, srv, "b-router")

	aNodeView, _ := srv.State().GetNodeByID(aNodeID)
	aRouterView, _ := srv.State().GetNodeByID(aRouterID)
	bRouterView, _ := srv.State().GetNodeByID(bRouterID)
	aMatchers, _ := srv.State().MatchersForNode(aNodeView)

	// A's node sees both of A's routes
	routes := srv.State().RoutesForPeer(aNodeView, aRouterView, aMatchers)
	require.True(t, slices.Contains(routes, r1), "a-node should see r1")
	require.True(t, slices.Contains(routes, r2), "a-node should see r2")

	// A's node does NOT see B's route
	routes = srv.State().RoutesForPeer(aNodeView, bRouterView, aMatchers)
	require.False(t, slices.Contains(routes, r3),
		"a-node should NOT see b-router's r3 (cross-tenant), got %v", routes)

	// All three are primary for their respective owners
	primaries := srv.State().GetNodePrimaryRoutes(aRouterID)
	require.True(t, slices.Contains(primaries, r1))
	require.True(t, slices.Contains(primaries, r2))

	bPrimaries := srv.State().GetNodePrimaryRoutes(bRouterID)
	require.True(t, slices.Contains(bPrimaries, r3))
}

// TestIPv6Routes verifies IPv6 subnet routes respect the same per-user
// isolation as IPv4 routes.
func TestIPv6Routes(t *testing.T) {
	srv := servertest.NewServer(t)

	userA := srv.CreateUser(t, "tenant-a")
	userB := srv.CreateUser(t, "tenant-b")

	aRouter := servertest.NewClient(t, srv, "a-r6", servertest.WithUser(userA))
	aNode := servertest.NewClient(t, srv, "a-node6", servertest.WithUser(userA))
	bRouter := servertest.NewClient(t, srv, "b-r6", servertest.WithUser(userB))

	aRouter.WaitForPeers(t, 2, routeIsoTimeout)
	aNode.WaitForPeers(t, 2, routeIsoTimeout)
	bRouter.WaitForPeers(t, 2, routeIsoTimeout)

	v6A := netip.MustParsePrefix("fd00:42::/48")
	v6B := netip.MustParsePrefix("fd00:43::/48")

	advertiseAndApproveRoute(t, srv, aRouter, v6A)
	advertiseAndApproveRoute(t, srv, bRouter, v6B)

	aNodeID := findNodeID(t, srv, "a-node6")
	aRouterID := findNodeID(t, srv, "a-r6")
	bRouterID := findNodeID(t, srv, "b-r6")

	aNodeView, _ := srv.State().GetNodeByID(aNodeID)
	aRouterView, _ := srv.State().GetNodeByID(aRouterID)
	bRouterView, _ := srv.State().GetNodeByID(bRouterID)
	aMatchers, _ := srv.State().MatchersForNode(aNodeView)

	// Same-user IPv6 visible
	routes := srv.State().RoutesForPeer(aNodeView, aRouterView, aMatchers)
	require.True(t, slices.Contains(routes, v6A),
		"a-node should see a-router's IPv6 route %s, got %v", v6A, routes)

	// Cross-user IPv6 isolated
	routes = srv.State().RoutesForPeer(aNodeView, bRouterView, aMatchers)
	require.False(t, slices.Contains(routes, v6B),
		"a-node should NOT see b-router's IPv6 route (cross-tenant), got %v", routes)

	// Primary election works for IPv6
	primaries := srv.State().GetNodePrimaryRoutes(aRouterID)
	require.True(t, slices.Contains(primaries, v6A))
}

// TestRouteOverlap verifies that overlapping routes (e.g. supernet in
// user A, subnet in user B) remain isolated — each user only sees their
// own approved prefix.
func TestRouteOverlap(t *testing.T) {
	srv := servertest.NewServer(t)

	userA := srv.CreateUser(t, "tenant-a")
	userB := srv.CreateUser(t, "tenant-b")

	aRouter := servertest.NewClient(t, srv, "a-super", servertest.WithUser(userA))
	aNode := servertest.NewClient(t, srv, "a-n", servertest.WithUser(userA))
	bRouter := servertest.NewClient(t, srv, "b-sub", servertest.WithUser(userB))

	aRouter.WaitForPeers(t, 2, routeIsoTimeout)
	aNode.WaitForPeers(t, 2, routeIsoTimeout)
	bRouter.WaitForPeers(t, 2, routeIsoTimeout)

	// A advertises 10.0.0.0/8 (supernet), B advertises 10.42.0.0/24 (subnet)
	supernet := netip.MustParsePrefix("10.0.0.0/8")
	subnet := netip.MustParsePrefix("10.42.0.0/24")

	advertiseAndApproveRoute(t, srv, aRouter, supernet)
	advertiseAndApproveRoute(t, srv, bRouter, subnet)

	aNodeID := findNodeID(t, srv, "a-n")
	aRouterID := findNodeID(t, srv, "a-super")
	bRouterID := findNodeID(t, srv, "b-sub")

	aNodeView, _ := srv.State().GetNodeByID(aNodeID)
	aRouterView, _ := srv.State().GetNodeByID(aRouterID)
	bRouterView, _ := srv.State().GetNodeByID(bRouterID)
	aMatchers, _ := srv.State().MatchersForNode(aNodeView)

	// A sees its own supernet
	routes := srv.State().RoutesForPeer(aNodeView, aRouterView, aMatchers)
	require.True(t, slices.Contains(routes, supernet))

	// A does NOT see B's subnet (different user, even though it's inside the supernet)
	routes = srv.State().RoutesForPeer(aNodeView, bRouterView, aMatchers)
	require.False(t, slices.Contains(routes, subnet),
		"A should NOT see B's subnet route (cross-tenant), got %v", routes)

	// Primary election is per-user, per-prefix — independent
	aPrimaries := srv.State().GetNodePrimaryRoutes(aRouterID)
	require.True(t, slices.Contains(aPrimaries, supernet))
	bPrimaries := srv.State().GetNodePrimaryRoutes(bRouterID)
	require.True(t, slices.Contains(bPrimaries, subnet))
}

// TestOfflineNodeLosesPrimary verifies that when a node goes offline, it
// is removed from the primary set and a healthy node (if any) takes over.
func TestOfflineNodeLosesPrimary(t *testing.T) {
	srv := servertest.NewServer(t)
	user := srv.CreateUser(t, "tenant")

	r1 := servertest.NewClient(t, srv, "r1", servertest.WithUser(user))
	r2 := servertest.NewClient(t, srv, "r2", servertest.WithUser(user))

	r1.WaitForPeers(t, 1, routeIsoTimeout)
	r2.WaitForPeers(t, 1, routeIsoTimeout)

	route := netip.MustParsePrefix("10.50.0.0/24")
	r1ID := advertiseAndApproveRoute(t, srv, r1, route)
	r2ID := advertiseAndApproveRoute(t, srv, r2, route)

	// r1 (lower ID) is primary
	require.True(t, slices.Contains(srv.State().GetNodePrimaryRoutes(r1ID), route))

	// r1 goes offline
	r1.Disconnect(t)

	// r2 should take over
	require.Eventually(t, func() bool {
		return slices.Contains(srv.State().GetNodePrimaryRoutes(r2ID), route)
	}, routeIsoTimeout, 200*time.Millisecond,
		"r2 should become primary after r1 goes offline")

	// r1 should no longer be primary
	require.False(t, slices.Contains(srv.State().GetNodePrimaryRoutes(r1ID), route))
}

// TestCrossUserHAPairs verifies that each user can independently have
// an HA pair for the same route, and failover in one user does not
// affect the other.
func TestCrossUserHAPairs(t *testing.T) {
	srv := servertest.NewServer(t)

	userA := srv.CreateUser(t, "tenant-a")
	userB := srv.CreateUser(t, "tenant-b")

	aR1 := servertest.NewClient(t, srv, "a-r1", servertest.WithUser(userA))
	aR2 := servertest.NewClient(t, srv, "a-r2", servertest.WithUser(userA))
	bR1 := servertest.NewClient(t, srv, "b-r1", servertest.WithUser(userB))
	bR2 := servertest.NewClient(t, srv, "b-r2", servertest.WithUser(userB))

	aR1.WaitForPeers(t, 3, routeIsoTimeout)
	aR2.WaitForPeers(t, 3, routeIsoTimeout)
	bR1.WaitForPeers(t, 3, routeIsoTimeout)
	bR2.WaitForPeers(t, 3, routeIsoTimeout)

	sameRoute := netip.MustParsePrefix("10.42.0.0/24")
	aR1ID := advertiseAndApproveRoute(t, srv, aR1, sameRoute)
	aR2ID := advertiseAndApproveRoute(t, srv, aR2, sameRoute)
	bR1ID := advertiseAndApproveRoute(t, srv, bR1, sameRoute)
	bR2ID := advertiseAndApproveRoute(t, srv, bR2, sameRoute)

	// Each user: lower-ID is primary
	require.True(t, slices.Contains(srv.State().GetNodePrimaryRoutes(aR1ID), sameRoute),
		"a-r1 should be primary in tenant-a")
	require.False(t, slices.Contains(srv.State().GetNodePrimaryRoutes(aR2ID), sameRoute),
		"a-r2 should NOT be primary while a-r1 is healthy")
	require.True(t, slices.Contains(srv.State().GetNodePrimaryRoutes(bR1ID), sameRoute),
		"b-r1 should be primary in tenant-b")
	require.False(t, slices.Contains(srv.State().GetNodePrimaryRoutes(bR2ID), sameRoute),
		"b-r2 should NOT be primary while b-r1 is healthy")

	// Failover in A: disconnect a-r1
	aR1.Disconnect(t)

	require.Eventually(t, func() bool {
		return slices.Contains(srv.State().GetNodePrimaryRoutes(aR2ID), sameRoute)
	}, routeIsoTimeout, 200*time.Millisecond,
		"a-r2 should take over in tenant-a")

	// B's primary should be UNCHANGED — b-r1 still primary
	require.True(t, slices.Contains(srv.State().GetNodePrimaryRoutes(bR1ID), sameRoute),
		"b-r1 should STILL be primary in tenant-b after A's failover")
	require.False(t, slices.Contains(srv.State().GetNodePrimaryRoutes(bR2ID), sameRoute),
		"b-r2 should STILL not be primary")
}
