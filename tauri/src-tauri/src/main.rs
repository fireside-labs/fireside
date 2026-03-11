// Valhalla Desktop — Tauri v2 main entry point
// Starts the Python backend (bifrost) and opens the dashboard webview.

#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::process::Command;
use std::thread;

fn main() {
    // Start Python backend in background
    thread::spawn(|| {
        let backend = if cfg!(target_os = "windows") {
            Command::new("python")
                .args(["bifrost.py"])
                .current_dir("../")
                .spawn()
        } else {
            Command::new("python3")
                .args(["bifrost.py"])
                .current_dir("../")
                .spawn()
        };

        match backend {
            Ok(mut child) => {
                println!("[valhalla] Backend started (PID: {:?})", child.id());
                let _ = child.wait();
            }
            Err(e) => {
                eprintln!("[valhalla] Failed to start backend: {}", e);
            }
        }
    });

    // Give backend a moment to start
    thread::sleep(std::time::Duration::from_millis(1500));

    // Launch Tauri webview
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
