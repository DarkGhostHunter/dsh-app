# AGENTS.md

Guidance for anyone (human or agent) changing this repository.

## What this project is

`dsh-app` wraps [deepseek-ai/deepseek-harness](https://github.com/deepseek-ai/deepseek-harness) into an Electron AppImage for Linux x64. Upstream ships its Desktop app for macOS and Windows only; this repository applies a small patch to a pristine upstream clone so upstream's *own* packaging pipeline produces the Linux artifact. There is no custom shell in this repository — an earlier Tauri port was deleted, and nothing like it should come back: upstream is deeply invested in Electron (updater, guests, platform view, shortcuts), and a second shell forks all of it.

Key files:

- `patches/linux-packaging.patch` — the only divergence from upstream. Registers the `linux-x64` release target, adapts the Linux Electron/CLI layouts, enables parallel release packing, skips the Office-conversion smoke check on Linux (no LibreOffice engine is published for Linux), and adjusts Linux window behavior (native decorations, no menu bar, close quits).
- `scripts/regenerate-patch.py` — the patch, expressed as exact-match text replacements. This is the source of truth for *how* the patch is made; the `.patch` file is its output.
- `scripts/local-build.sh` — local replica of the CI build.
- `.github/workflows/build-appimage.yml` — builds and publishes per upstream tag (manual, hourly watcher, or `repository_dispatch`).
- `.github/workflows/watch-upstream.yml` — hourly poller that dispatches builds for new upstream tags.
- `.github/workflows/check-patch-drift.yml` — weekly check that the patch still applies to the latest upstream tag; opens an issue on drift.

## When the patch drifts

`git apply` is atomic: the build fails loudly at the patch step, and releases simply stop following upstream until the patch is fixed. Never make the build skip or weaken a failed patch — an unpatched clone has no Linux target, and a half-applied one produces an app that silently lies about its behavior.

To fix drift:

1. Check out the drifted upstream tag in the clone: `git -C deepseek-harness fetch --depth 1 origin <tag> && git -C deepseek-harness checkout <tag>` (or edit the tag in `scripts/local-build.sh` and run its clone step).
2. Run `python3 scripts/regenerate-patch.py`. It resets the clone to pristine, then applies each replacement by exact anchor. The first anchor that no longer exists names the file and snippet upstream changed — that is the drift, with no searching required.
3. Fix the drifted replacement in `scripts/regenerate-patch.py` to express the same intent against upstream's new code. Read the new surrounding code first: if upstream changed the *behavior* being patched (not just moved it), decide whether the patch intent still makes sense before re-anchoring it.
4. Rerun the script until it reports zero drift. Verify intent, not just application: `bash scripts/local-build.sh` must complete, and the packaged smoke test must pass ("Host boot, frontend and plugin checks passed").
5. Run the app once (`--appimage-extract-and-run`) if the drift touched `main.ts`, `welcome-window.ts` or the smoke scripts.
6. Commit the regenerated patch together with the script change, push, and dispatch `build-appimage.yml` for the tag that failed.

When upstream ships its own `linux-x64` target, the packaging half of the patch becomes obsolete: drop those replacements and keep only what upstream would never take as-is (the Office-conversion skip and the Linux window behavior).

## Rules for any change

- **Respect upstream.** Everything upstream-related lives in the patch; nothing outside it may modify behavior. Every replacement in `scripts/regenerate-patch.py` needs a one-line comment saying why it exists — if the reason disappears upstream, the replacement should too.
- **Keep the patch minimal.** Prefer deleting a replacement over keeping it "just in case". A smaller patch drifts less.
- **Prove it builds.** For any change to the patch, the workflows or the build scripts: run `bash scripts/local-build.sh` end to end. Success is the AppImage file appearing in `deepseek-harness/apps/desktop/.desktop-build/targets/linux-x64/unsigned-artifacts/` and the log ending with the packaged smoke test passing. A patch change that has not passed a local build is not done.
- **Prove the patch regenerates.** After editing `scripts/regenerate-patch.py`, run it and confirm the diff against the previous `patches/linux-packaging.patch` contains only the intended change. `python3 scripts/regenerate-patch.py --check` must pass against a pristine clone.
- **CI is the final gate.** Push, dispatch `build-appimage.yml` with the target tag, and confirm the run succeeds and the release asset was refreshed. Do not consider work finished on a local build alone.
