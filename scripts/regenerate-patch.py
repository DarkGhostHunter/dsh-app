#!/usr/bin/env python3
"""Regenerate patches/linux-packaging.patch against a pristine upstream clone.

The patch is a list of exact-match text replacements. Each anchor is asserted:
the first anchor that no longer exists IS the drift signal — it names the file
and the snippet upstream changed. Fix that one replacement, rerun, done.

Usage:
  python3 scripts/regenerate-patch.py            # regenerate the patch
  python3 scripts/regenerate-patch.py --check    # verify the current patch applies

Requires a clone at deepseek-harness/ checked out at the target tag. The script
resets the clone to pristine first, so local edits there are discarded.
"""

import argparse
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
CLONE = ROOT / 'deepseek-harness'
PATCH = ROOT / 'patches' / 'linux-packaging.patch'

# Every replacement that makes up the Linux packaging patch, in application
# order. (relpath, old, new) — `old` must match the pristine upstream text.
EDITS = [
    # --- Register the linux-x64 release target ---
    ('apps/desktop/scripts/desktop-build-paths.mjs',
     "const SUPPORTED_TARGETS = new Set(['mac-arm64', 'mac-x64', 'win-x64'])",
     "const SUPPORTED_TARGETS = new Set(['mac-arm64', 'mac-x64', 'win-x64', 'linux-x64'])"),
    ('apps/desktop/scripts/desktop-build-paths.mjs',
     " * @returns {{ platform: 'darwin' | 'win32', arch: 'arm64' | 'x64' }}",
     " * @returns {{ platform: 'darwin' | 'win32' | 'linux', arch: 'arm64' | 'x64' }}"),
    ('apps/desktop/scripts/desktop-build-paths.mjs',
     "    platform: /** @type {'darwin' | 'win32'} */ (target === 'win-x64' ? 'win32' : 'darwin'),",
     "    platform: /** @type {'darwin' | 'win32' | 'linux'} */ (target === 'win-x64' ? 'win32' : target === 'linux-x64' ? 'linux' : 'darwin'),"),
    ('apps/desktop/scripts/desktop-build-paths.d.mts',
     "  readonly platform: 'darwin' | 'win32'",
     "  readonly platform: 'darwin' | 'win32' | 'linux'"),
    ('apps/desktop/scripts/desktop-auto-update-environment.mjs',
     "const UPDATE_TARGETS = new Set(['mac-arm64', 'mac-x64', 'win-x64'])",
     "const UPDATE_TARGETS = new Set(['mac-arm64', 'mac-x64', 'win-x64', 'linux-x64'])"),
    ('apps/desktop/scripts/desktop-auto-update-environment.d.mts',
     "export type DesktopAutoUpdateTarget = 'mac-arm64' | 'mac-x64' | 'win-x64'",
     "export type DesktopAutoUpdateTarget = 'mac-arm64' | 'mac-x64' | 'win-x64' | 'linux-x64'"),
    ('apps/desktop/scripts/package-target.ts',
     "export type DesktopPackageTargetName = 'mac-arm64' | 'mac-x64' | 'win-x64'",
     "export type DesktopPackageTargetName = 'mac-arm64' | 'mac-x64' | 'win-x64' | 'linux-x64'"),
    ('apps/desktop/scripts/package-target.ts',
     "readonly platform: 'darwin' | 'win32'",
     "readonly platform: 'darwin' | 'win32' | 'linux'"),
    ('apps/desktop/scripts/package-target.ts',
     """  'win-x64': {
    name: 'win-x64',
    platform: 'win32',
    arch: 'x64',
    builderPlatform: '--win',
    builderArch: '--x64',
  },
}""",
     """  'win-x64': {
    name: 'win-x64',
    platform: 'win32',
    arch: 'x64',
    builderPlatform: '--win',
    builderArch: '--x64',
  },
  'linux-x64': {
    name: 'linux-x64',
    platform: 'linux',
    arch: 'x64',
    builderPlatform: '--linux',
    builderArch: '--x64',
  },
}"""),
    ('apps/desktop/scripts/package-target.ts',
     "  if (name === 'mac-arm64' && hostArch !== 'arm64') {",
     """  if (name === 'linux-x64' && hostPlatform !== 'linux') {
    throw new Error('desktop package: linux-x64 requires a Linux build host')
  }
  if (name === 'mac-arm64' && hostArch !== 'arm64') {"""),
    ('apps/desktop/scripts/package-target.ts',
     "readonly builderPlatform: '--mac' | '--win'",
     "readonly builderPlatform: '--mac' | '--win' | '--linux'"),
    ('apps/desktop/scripts/package-target.ts',
     "const environment = target.platform === 'darwin' && invocation.unsigned\n    ? localMacOSPackageEnvironment()",
     "const environment = target.platform !== 'win32' && invocation.unsigned\n    ? localMacOSPackageEnvironment()"),
    ('apps/desktop/scripts/package-target.ts',
     "  const packArguments = mac === undefined ? [] : ['--concurrency', String(mac.packConcurrency)]",
     """  // macOS packs with its preset concurrency; Linux passes an explicit bound since
  // the default (1) packs the release families one tarball at a time.
  const packArguments = mac === undefined
    ? target.platform === 'linux' ? ['--concurrency', '4'] : []
    : ['--concurrency', String(mac.packConcurrency)]"""),
    ('apps/desktop/scripts/desktop-package-environment.mjs',
     "  if (target.platform !== 'darwin' || !options.unsigned) resolveDesktopPolicyEnvironment(environment)",
     "  if (target.platform === 'win32' || !options.unsigned) resolveDesktopPolicyEnvironment(environment)"),
    ('apps/desktop/scripts/desktop-package-environment.mjs',
     "  if (target.platform === 'darwin') resolveMacOSPackageSettings(environment)\n  else resolveWindowsPackageSettings(environment)",
     "  if (target.platform === 'darwin') resolveMacOSPackageSettings(environment)\n  else if (target.platform === 'win32') resolveWindowsPackageSettings(environment)"),
    ('apps/desktop/scripts/desktop-package-environment.d.mts',
     "  platform: 'win32' | 'darwin',",
     "  platform: 'win32' | 'darwin' | 'linux',"),
    ('apps/desktop/scripts/desktop-package-environment.d.mts',
     "  target: { platform: 'win32' | 'darwin', arch: string },",
     "  target: { platform: 'win32' | 'darwin' | 'linux', arch: string },"),
    ('apps/desktop/scripts/desktop-release-store.ts',
     "  target: z.enum(['mac-arm64', 'mac-x64', 'win-x64']),",
     "  target: z.enum(['mac-arm64', 'mac-x64', 'win-x64', 'linux-x64']),"),
    ('apps/desktop/scripts/desktop-upload-plan.ts',
     "  'win-x64': { platform: 'win32', arch: 'x64', os: 'win' },\n}",
     "  'win-x64': { platform: 'win32', arch: 'x64', os: 'win' },\n  'linux-x64': { platform: 'linux', arch: 'x64', os: 'linux' },\n}"),
    ('apps/desktop/scripts/desktop-toolchain-preflight.ts',
     "export async function probeDesktopToolchain(\n  platform: 'darwin' | 'win32',",
     "export async function probeDesktopToolchain(\n  platform: 'darwin' | 'win32' | 'linux',"),
    ('apps/desktop/scripts/desktop-toolchain-preflight.ts',
     "export async function requireDesktopToolchain(\n  platform: 'darwin' | 'win32',",
     "export async function requireDesktopToolchain(\n  platform: 'darwin' | 'win32' | 'linux',"),
    # --- Linux Electron executable layout ---
    ('apps/desktop/scripts/prepare-dsh.ts',
     "const NODE = join(BUILD_PATHS.electron, process.platform === 'win32' ? 'electron.exe' : 'Electron.app/Contents/MacOS/Electron')",
     "const NODE = join(BUILD_PATHS.electron, process.platform === 'win32' ? 'electron.exe' : process.platform === 'linux' ? 'electron' : 'Electron.app/Contents/MacOS/Electron')"),
    ('apps/desktop/scripts/prepare-runtime.ts',
     "const executable = join(BUILD_PATHS.electron, platform === 'win32' ? 'electron.exe' : 'Electron.app/Contents/MacOS/Electron')",
     "const executable = join(BUILD_PATHS.electron, platform === 'win32' ? 'electron.exe' : platform === 'linux' ? 'electron' : 'Electron.app/Contents/MacOS/Electron')"),
    ('apps/desktop/scripts/prepare-cli.ts',
     "export function prepareDesktopCli(destination: string, platform: 'darwin' | 'win32'): void {",
     "export function prepareDesktopCli(destination: string, platform: 'darwin' | 'win32' | 'linux'): void {"),
    ('apps/desktop/scripts/prepare-cli.ts',
     "  if (platform === 'darwin') chmodSync(command, 0o755)",
     "  if (platform !== 'win32') chmodSync(command, 0o755)"),
    ('apps/desktop/cli/dsh',
     'ELECTRON_RUN_AS_NODE=1 exec "$resources/../MacOS/DeepSeek Harness" --expose-internals',
     '''case "$(uname -s)" in
  Darwin) binary="$resources/../MacOS/DeepSeek Harness" ;;
  *) binary="$resources/deepseek-harness" ;;
esac
ELECTRON_RUN_AS_NODE=1 exec "$binary" --expose-internals'''),
    ('apps/desktop/scripts/smoke-packaged-runtime.ts',
     """const application = windows ? join(artifacts, 'win-unpacked')
  : join(artifacts, target === 'mac-arm64' ? 'mac-arm64' : 'mac', 'DeepSeek Harness.app', 'Contents')
const resources = join(application, windows ? 'resources' : 'Resources')
const executable = windows ? join(application, 'DeepSeek Harness.exe') : join(application, 'MacOS', 'DeepSeek Harness')""",
     """const linux = target === 'linux-x64'
const application = windows ? join(artifacts, 'win-unpacked')
  : linux ? join(artifacts, 'linux-unpacked')
  : join(artifacts, target === 'mac-arm64' ? 'mac-arm64' : 'mac', 'DeepSeek Harness.app', 'Contents')
const resources = join(application, windows || linux ? 'resources' : 'Resources')
const executable = windows ? join(application, 'DeepSeek Harness.exe')
  : linux ? join(application, 'deepseek-harness')
  : join(application, 'MacOS', 'DeepSeek Harness')"""),
    # --- electron-builder: Linux block gets an icon and executable name ---
    ('apps/desktop/scripts/electron-builder-config.mjs',
     """    linux: {
      category: 'Development',
      target: ['AppImage'],
    },""",
     """    linux: {
      category: 'Development',
      target: ['AppImage'],
      icon: fileURLToPath(new URL('../resources/icon.png', import.meta.url)),
      executableName: 'deepseek-harness',
    },"""),
    ('apps/desktop/scripts/electron-builder-config.mjs',
     "  const policy = packagesMacOS && unsigned ? undefined : resolveDesktopPolicyEnvironment(env)",
     "  const policy = (packagesMacOS || resolvedPlatform === 'linux') && unsigned ? undefined : resolveDesktopPolicyEnvironment(env)"),
    # --- Smoke test: no Linux LibreOffice engine is published, skip conversion ---
    ('apps/desktop/scripts/smoke-runtime.ts',
     """    const inputs = ['docx', 'xlsx', 'pptx'].map(extension => ({ extension,
      bytes: readFileSync(join(home, `input.${extension}`)).toString('base64') }))""",
     """    // No Linux LibreOffice engine is published, so conversion fixtures are only exercised off Linux.
    const inputs = process.platform === 'linux' ? [] : ['docx', 'xlsx', 'pptx'].map(extension => ({ extension,
      bytes: readFileSync(join(home, `input.${extension}`)).toString('base64') }))"""),
    ('apps/desktop/scripts/smoke-runtime.ts',
     """    const cliResponse = await fetch(new URL('/desktop-smoke-office-cli', ready.url), {
      headers: { cookie }, signal: AbortSignal.timeout(120_000),
    })
    if (!cliResponse.ok) throw new Error(`desktop runtime: skill CLI failed: ${await cliResponse.text()}`)
    const cliResult = await cliResponse.json() as { capabilities: { runtime: { cliPath: string } }; pdf: string }
    if (!cliResult.capabilities.runtime.cliPath.endsWith('cli.js') || Buffer.from(cliResult.pdf, 'base64').subarray(0, 5).toString() !== '%PDF-') {
      throw new Error('desktop runtime: skill CLI did not return capabilities and a PDF')
    }
    console.log('desktop runtime: DOCX, XLSX, PPTX to PDF and skill CLI discovery passed')""",
     """    if (process.platform !== 'linux') {
      const cliResponse = await fetch(new URL('/desktop-smoke-office-cli', ready.url), {
        headers: { cookie }, signal: AbortSignal.timeout(120_000),
      })
      if (!cliResponse.ok) throw new Error(`desktop runtime: skill CLI failed: ${await cliResponse.text()}`)
      const cliResult = await cliResponse.json() as { capabilities: { runtime: { cliPath: string } }; pdf: string }
      if (!cliResult.capabilities.runtime.cliPath.endsWith('cli.js') || Buffer.from(cliResult.pdf, 'base64').subarray(0, 5).toString() !== '%PDF-') {
        throw new Error('desktop runtime: skill CLI did not return capabilities and a PDF')
      }
      console.log('desktop runtime: DOCX, XLSX, PPTX to PDF and skill CLI discovery passed')
    } else {
      console.log('desktop runtime: Host boot, frontend and plugin checks passed; Office conversion skipped (no published Linux engine)')
    }"""),
    # --- Linux desktop behavior: no menu bar, close quits ---
    ('apps/desktop/src/main.ts',
     "    Menu.setApplicationMenu(Menu.buildFromTemplate(process.platform === 'win32' ? devToolsItems : [{",
     "    Menu.setApplicationMenu(Menu.buildFromTemplate(process.platform === 'darwin' ? [{"),
    ('apps/desktop/src/main.ts',
     """    Menu.setApplicationMenu(Menu.buildFromTemplate(process.platform === 'darwin' ? [{
      label: darwin ? app.name : currentDesktopLocale().messages.application,
      submenu: [...applicationItems(), ...devToolsItems],
    }, ...platformMenus()]))""",
     """    Menu.setApplicationMenu(Menu.buildFromTemplate(process.platform === 'darwin' ? [{
      label: app.name,
      submenu: [...applicationItems(), ...devToolsItems],
    }, ...platformMenus()] : devToolsItems))"""),
    ('apps/desktop/src/main.ts',
     """  const createMainWindow = (): BrowserWindow => {
    const window = createWindow(appPreload, false, true)
    mainWindow = window""",
     """  const createMainWindow = (): BrowserWindow => {
    const window = createWindow(appPreload, false, true)
    // The DevTools-only menu exists for its accelerators; Linux never renders its bar.
    if (process.platform === 'linux') window.setMenuBarVisibility(false)
    mainWindow = window"""),
    ('apps/desktop/src/main.ts',
     """    window.on('close', (event) => {
      if (quitting || shellInstallerOwnsQuit || sessionEnding) return
      event.preventDefault()""",
     """    window.on('close', (event) => {
      if (quitting || shellInstallerOwnsQuit || sessionEnding) return
      if (process.platform === 'linux') { app.quit(); return }
      event.preventDefault()"""),
]


def run(*args: str, cwd: pathlib.Path) -> None:
    subprocess.run(args, cwd=cwd, check=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true',
                        help='only verify the committed patch applies to a pristine clone')
    args = parser.parse_args()

    if not (CLONE / '.git').exists():
        print(f'error: {CLONE} is not a git clone; run scripts/local-build.sh first', file=sys.stderr)
        return 2

    if args.check:
        run('git', 'checkout', '--', '.', cwd=CLONE)
        try:
            run('git', 'apply', '--check', '--verbose', str(pathlib.Path('..') / PATCH.relative_to(ROOT)), cwd=CLONE)
        except subprocess.CalledProcessError:
            print('PATCH DRIFT: the patch no longer applies to this upstream tag.', file=sys.stderr)
            return 1
        run('git', 'checkout', '--', '.', cwd=CLONE)
        print(f'patch applies cleanly to {CLONE.resolve()} at its current checkout')
        return 0

    run('git', 'checkout', '--', '.', cwd=CLONE)
    drift = []
    for rel, old, new in EDITS:
        path = CLONE / rel
        text = path.read_text()
        if new in text and old not in text:
            continue  # already applied
        if old not in text:
            drift.append(rel)
            print(f'DRIFT in {rel}: anchor not found:\n  {old.splitlines()[0][:100]}', file=sys.stderr)
            continue
        path.write_text(text.replace(old, new, 1))
    if drift:
        print(f'\n{len(drift)} file(s) drifted; fix the replacements above and rerun.', file=sys.stderr)
        return 1
    diff = subprocess.run(['git', 'diff'], cwd=CLONE, check=True, capture_output=True, text=True).stdout
    PATCH.parent.mkdir(exist_ok=True)
    PATCH.write_text(diff)
    files = len({line.split(' b/')[0][11:] for line in diff.splitlines() if line.startswith('diff --git')})
    print(f'wrote {PATCH.relative_to(ROOT)} ({files} files, {diff.count(chr(10) + "@@")} hunks)')
    print('verify locally with: bash scripts/local-build.sh')
    return 0


if __name__ == '__main__':
    sys.exit(main())
