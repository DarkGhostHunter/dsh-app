#!/usr/bin/env bash
# Local replica of .github/workflows/build-appimage.yml: clone upstream at a
# tag, apply the Linux packaging patch, and run upstream's own Desktop
# packaging pipeline for linux-x64. Takes the upstream tag as $1 (default:
# latest dsh-v* tag).
set -euo pipefail
cd "$(dirname "$0")/.."

TAG="${1:-$(gh api repos/deepseek-ai/deepseek-harness/tags --jq '[.[].name | select(test("^dsh-v[0-9]+\\.[0-9]+\\.[0-9]+(-[0-9A-Za-z.-]+)?$"))][0]')}"
echo "Building upstream tag: $TAG"

rm -rf deepseek-harness
git clone --depth 1 --branch "$TAG" \
  https://github.com/deepseek-ai/deepseek-harness.git deepseek-harness

cd deepseek-harness
pnpm install --frozen-lockfile
git apply ../patches/linux-packaging.patch

# Upstream's own pipeline: workspace build, runtime preparation, dsh tree,
# electron-builder AppImage, packaged smoke test. Unsigned keeps the run free
# of macOS/Windows signing credentials, which Linux never needed anyway.
pnpm --filter @deepseek-ai/dsh-desktop run package -- linux-x64 --unsigned

echo
echo "AppImage: apps/desktop/.desktop-build/targets/linux-x64/unsigned-artifacts/"
ls -lh apps/desktop/.desktop-build/targets/linux-x64/unsigned-artifacts/*.AppImage
