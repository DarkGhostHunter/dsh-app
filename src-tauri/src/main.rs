#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::io::{BufRead, BufReader};
use std::path::PathBuf;
use std::process::{Child, Command, Stdio};
use std::sync::Mutex;

use tauri::Manager;

/// The sidecar `dsh web` process, killed when the app exits.
struct DshProcess(Mutex<Option<Child>>);

/// Directory holding the bundled harness workspace: `apps/cli/lib/bin.js`
/// and the installed workspace `node_modules`. `DSH_RUNTIME_DIR` overrides
/// it so dev runs can point at a local deepseek-harness clone.
fn workspace_root(app: &tauri::AppHandle) -> PathBuf {
    std::env::var("DSH_RUNTIME_DIR").map(PathBuf::from).unwrap_or_else(|_| {
        app.path()
            .resource_dir()
            .expect("no resource directory")
            .join("dsh")
    })
}

/// The Node interpreter bundled next to the workspace (`node/bin/node`).
/// Falls back to `PATH` so dev runs can use the system Node.
fn node_bin(app: &tauri::AppHandle) -> PathBuf {
    let bundled = app
        .path()
        .resource_dir()
        .map(|dir| dir.join("node").join("bin").join("node"));
    match (std::env::var("DSH_RUNTIME_DIR"), bundled) {
        (Ok(_), Ok(node)) if node.exists() => node,
        (_, Ok(node)) if node.exists() => node,
        _ => PathBuf::from("node"),
    }
}

fn spawn_dsh(app: &tauri::AppHandle) -> Result<Child, Box<dyn std::error::Error>> {
    let root = workspace_root(app);
    let bin = root.join("apps").join("cli").join("lib").join("bin.js");
    Ok(Command::new(node_bin(app))
        .arg(bin)
        .args(["web", "--no-open", "--port", "0"])
        .current_dir(&root)
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
