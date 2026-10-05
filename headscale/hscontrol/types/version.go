package types

import (
	"fmt"
	"runtime"
	"runtime/debug"
	"strings"
	"sync"
)

type GoInfo struct {
	Version string `json:"version"`
	OS      string `json:"os"`
	Arch    string `json:"arch"`
}

type VersionInfo struct {
	Version   string `json:"version"`
	Commit    string `json:"commit"`
	BuildTime string `json:"buildTime"`
	Go        GoInfo `json:"go"`
	Dirty     bool   `json:"dirty"`
}

func (v *VersionInfo) String() string {
	var sb strings.Builder

	version := v.Version
	if v.Dirty && !strings.Contains(version, "dirty") {
		version += "-dirty"
	}

	fmt.Fprintf(&sb, "headscale version %s\n", version)
	fmt.Fprintf(&sb, "commit: %s\n", v.Commit)
	fmt.Fprintf(&sb, "build time: %s\n", v.BuildTime)
	fmt.Fprintf(&sb, "built with: %s %s/%s\n", v.Go.Version, v.Go.OS, v.Go.Arch)

	return sb.String()
}

var buildInfo = sync.OnceValues(debug.ReadBuildInfo)

// Version, Commit and BuildTime are filled in at build time by the panel's
// Dockerfile (-ldflags -X). Version is the upstream headscale release this
// source tree corresponds to, taken from the top entry of CHANGELOG.md; the
// other two identify the panel repository commit the image was built from.
// They are empty in every other build, where these fields keep coming from
// [debug.ReadBuildInfo].
//
// PATCH: added by Headscale-Admin-Pro. The panel builds this tree in a Docker
// context with no .git, so the toolchain stamps no vcs.* settings and reports
// Main.Version as "(devel)" — without an injection the binary answers "dev",
// and headscale skips its database version gate for dev builds. A conflict
// here on `git subtree pull` is expected; see headscale/MERGING-UPSTREAM.md.
var (
	Version   = ""
	Commit    = ""
	BuildTime = ""
)

var GetVersionInfo = sync.OnceValue(func() *VersionInfo {
	info := &VersionInfo{
		Version:   "dev",
		Commit:    "unknown",
		BuildTime: "unknown",
		Go: GoInfo{
			Version: runtime.Version(),
			OS:      runtime.GOOS,
			Arch:    runtime.GOARCH,
		},
		Dirty: false,
	}

	buildInfo, ok := buildInfo()
	if !ok {
		return info
	}

	// Extract version from module path or main version
	if buildInfo.Main.Version != "" && buildInfo.Main.Version != "(devel)" {
		info.Version = buildInfo.Main.Version
	}

	// Extract build settings
	for _, setting := range buildInfo.Settings {
		switch setting.Key {
		case "vcs.revision":
			info.Commit = setting.Value
		case "vcs.modified":
			info.Dirty = setting.Value == "true"
		case "vcs.time":
			info.BuildTime = setting.Value
		}
	}

	// Values injected at build time win over everything the toolchain
	// stamped, so this has to come last: a Docker build has no .git and is
	// therefore the one case where the injections are the only source, but
	// they must not be overwritten by a vcs.* setting either.
	if Version != "" {
		info.Version = Version
	}

	if Commit != "" {
		info.Commit = Commit
	}

	if BuildTime != "" {
		info.BuildTime = BuildTime
	}

	return info
})
