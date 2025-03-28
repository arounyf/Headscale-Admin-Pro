#!/bin/sh
/command/s6-svstat /run/s6-rc/servicedirs/adminui || exit 1
/command/s6-svstat /run/s6-rc/servicedirs/headscale || exit 1