
## Test server (192.168.6.12)

MANDATORY: hot-swap `/app` files only. Never rebuild/recreate the container
unless the user explicitly says so.

- Flask changes → rsync to `/root/hs-admin/app/`, then `docker restart hs-admin`
- headscale binary → scp to `/root/hs-admin/app/headscale`, then replace inside container
- Client testing → 192.168.6.63, use tailscaled with `--state=mem:` and unique `--statedir`
