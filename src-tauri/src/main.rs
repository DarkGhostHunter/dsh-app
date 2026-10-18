#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use tauri::Manager;

fn main() {
  tauri::Builder::default()
    .setup(|app| {
      let handle = app.handle();
      // Optionally: trigger an update check at startup from Rust side
      // tauri::updater::check().run(&handle);
      Ok(())
    })
    .run(tauri::generate_context!())
    .expect("error while running tauri application");
}