#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::io::{BufRead, BufReader};
use std::path::PathBuf;
use std::process::{Child, Command, Stdio};
use std::sync::Mutex;

use tauri::Manager;

/// The sidecar `dsh web` process, killed when the app exits.
struct DshProcess(Mutex<Option<Child>>);

/// Directory holding the extracted runtime: `dsh/` (the harness workspace
/// with `apps/cli/lib/bin.js` and its `node_modules`) and `node/bin/node`.
/// `DSH_RUNTIME_DIR` overrides it so dev runs can point at a local
/// deepseek-harness clone and the system Node.
fn runtime_root(app: &tauri::AppHandle) -> PathBuf {
    std::env::var("DSH_RUNTIME_DIR").map(PathBuf::from).unwrap_or_else(|_| {
        app.path()
            .app_data_dir()
            .expect("no app data directory")
            .join("runtime")
    })
}

/// Extract `resources/runtime.tar` into the app-data runtime directory on
/// first launch. The payload ships as one archive because linuxdeploy scans
/// every ELF in the AppDir and node_modules contains dozens it cannot deploy
/// (static esbuild builds, musl variants, foreign-arch prebuilds).
fn ensure_runtime_extracted(app: &tauri::AppHandle) -> Result<(), Box<dyn std::error::Error>> {
    let root = runtime_root(app);
    let marker = root.join("dsh").join("apps").join("cli").join("lib").join("bin.js");
    if marker.exists() {
        return Ok(());
    }
    let archive = app
        .path()
        .resource_dir()?
        .join("runtime.tar");
    std::fs::create_dir_all(&root)?;
    let status = Command::new("tar")
        .arg("-xf")
        .arg(&archive)
        .arg("-C")
        .arg(&root)
        .status()?;
    if !status.success() {
        return Err(format!("runtime extraction failed: {status}").into());
    }
    Ok(())
}

fn spawn_dsh(app: &tauri::AppHandle) -> Result<Child, Box<dyn std::error::Error>> {
    let root = runtime_root(app);
    let bin = root.join("dsh").join("apps").join("cli").join("lib").join("bin.js");
    let node = root.join("node").join("bin").join("node");
    let node = if node.exists() { node } else { PathBuf::from("node") };
    Ok(Command::new(node)
        .arg(bin)
        .args(["web", "--no-open", "--port", "0"])
        .current_dir(root.join("dsh"))
        .env("NODE_ENV", "production")
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()?)
}

/// Parse `dsh web: http://127.0.0.1:PORT/?token=...` from a log line.
fn boot_url(line: &str) -> Option<String> {
    line.split_whitespace()
        .find(|part| part.starts_with("http://127.0.0.1:") && part.contains("token="))
        .map(ToOwned::to_owned)
}

fn main() {
    tauri::Builder::default()
        .manage(DshProcess(Mutex::new(None)))
        .setup(|app| {
            let handle = app.handle().clone();
            ensure_runtime_extracted(&handle)?;
            let mut child = spawn_dsh(&handle)?;
            let stdout = child.stdout.take().expect("piped stdout");
            *handle.state::<DshProcess>().0.lock().unwrap() = Some(child);

            // The child prints the boot URL once the Host is listening;
            // navigate the webview there and keep relaying the log.
            std::thread::spawn(move || {
                for line in BufReader::new(stdout).lines().map_while(Result::ok) {
                    println!("dsh: {line}");
                    if let Some(url) = boot_url(&line) {
                        if let Some(window) = handle.get_webview_window("main") {
                            let script = format!("window.location.replace('{url}')");
                            let _ = window.eval(&script);
                        }
                    }
                }
            });
            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("error while building tauri application")
        .run(|app, event| {
            if let tauri::RunEvent::Exit = event {
                if let Some(mut child) = app.state::<DshProcess>().0.lock().unwrap().take() {
                    let _ = child.kill();
                    let _ = child.wait();
                }
            }
        });
}
