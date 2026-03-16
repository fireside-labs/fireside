// Fireside Desktop — Tauri v2 entry point
// Native installer wizard + backend launcher.

#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use serde::Serialize;
use std::fs;
use std::path::PathBuf;
use std::process::Command;

// ---------------------------------------------------------------------------
// Data structures
// ---------------------------------------------------------------------------

#[derive(Serialize)]
struct SystemInfo {
    ram_gb: f64,
    vram_gb: f64,
    gpu: String,
    os: String,
    arch: String,
}

#[derive(serde::Deserialize)]
struct FiresideConfig {
    user_name: String,
    agent_name: String,
    agent_style: String,
    companion_species: String,
    companion_name: String,
    brain: String,
    model: String,
}

// ---------------------------------------------------------------------------
// Task 2 — Tauri Rust Commands
// ---------------------------------------------------------------------------

/// Return system hardware info for the install wizard.
#[tauri::command]
fn get_system_info() -> SystemInfo {
    let ram_gb = {
        #[cfg(target_os = "windows")]
        {
            let output = Command::new("powershell")
                .args(["-NoProfile", "-Command",
                    "(Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory"])
                .output();
            match output {
                Ok(o) => {
                    let s = String::from_utf8_lossy(&o.stdout);
                    s.trim()
                        .parse::<f64>()
                        .map(|b| (b / 1_073_741_824.0 * 10.0).round() / 10.0)
                        .unwrap_or(0.0)
                }
                Err(_) => 0.0,
            }
        }
        #[cfg(not(target_os = "windows"))]
        {
            let output = Command::new("sysctl").args(["-n", "hw.memsize"]).output();
            match output {
                Ok(o) => {
                    let s = String::from_utf8_lossy(&o.stdout);
                    s.trim()
                        .parse::<f64>()
                        .map(|b| (b / 1_073_741_824.0 * 10.0).round() / 10.0)
                        .unwrap_or(0.0)
                }
                Err(_) => 0.0,
            }
        }
    };

    // Detect GPU and VRAM
    let (gpu, vram_gb) = {
        #[cfg(target_os = "windows")]
        {
            // 1. Try nvidia-smi with absolute path first (most accurate for NVIDIA)
            let nvsmi_path = "C:\\Windows\\System32\\nvidia-smi.exe";
            let nvidia_data = Command::new(nvsmi_path)
                .args(["--query-gpu=name,memory.total", "--format=csv,noheader,nounits"])
                .output()
                .ok()
                .and_then(|o| {
                    let s = String::from_utf8_lossy(&o.stdout).trim().to_string();
                    if s.is_empty() { return None; }
                    let first_line = s.lines().next()?;
                    let parts: Vec<&str> = first_line.split(',').collect();
                    if parts.len() >= 2 {
                        let name = parts[0].trim().to_string();
                        let mb = parts[1].trim().parse::<f64>().ok()?;
                        let gb = (mb / 1024.0 * 10.0).round() / 10.0;
                        Some((name, gb))
                    } else {
                        None
                    }
                });

            if let Some(data) = nvidia_data {
                data
            } else {
                // 2. Fallback to WMI, but find the BEST GPU (max AdapterRAM)
                let wmi_data = Command::new("powershell")
                    .args(["-NoProfile", "-Command",
                        "Get-CimInstance Win32_VideoController | Select-Object Name, AdapterRAM | ConvertTo-Json"])
                    .output()
                    .ok()
                    .and_then(|o| {
                        let s = String::from_utf8_lossy(&o.stdout).trim().to_string();
                        if s.is_empty() { return None; }
                        // Handle both single object and array
                        if s.starts_with('[') {
                            let list: Vec<serde_json::Value> = serde_json::from_str(&s).ok()?;
                            list.into_iter().max_by_key(|v| v["AdapterRAM"].as_f64().unwrap_or(0.0) as u64)
                        } else {
                            serde_json::from_str(&s).ok()
                        }
                    });

                match wmi_data {
                    Some(v) => {
                        let name = v["Name"].as_str().unwrap_or("Unknown").to_string();
                        let b = v["AdapterRAM"].as_f64().unwrap_or(0.0);
                        let gb = (b / 1_073_741_824.0 * 10.0).round() / 10.0;
                        (name, gb)
                    }
                    None => ("Unknown".into(), 0.0)
                }
            }
        }
        #[cfg(target_os = "macos")]
        {
            // Apple Silicon: detect chipset name + unified memory as VRAM
            let gpu_name = Command::new("system_profiler")
                .args(["SPDisplaysDataType"])
                .output()
                .ok()
                .and_then(|o| {
                    let s = String::from_utf8_lossy(&o.stdout).to_string();
                    s.lines()
                        .find(|l| l.contains("Chipset Model:"))
                        .map(|l| l.split(':').nth(1).unwrap_or("Unknown").trim().to_string())
                })
                .unwrap_or_else(|| "Apple Silicon".into());

            let vram = Command::new("sysctl")
                .args(["-n", "hw.memsize"])
                .output()
                .ok()
                .and_then(|o| {
                    let s = String::from_utf8_lossy(&o.stdout).trim().to_string();
                    s.parse::<f64>().ok()
                })
                .map(|b| (b / 1_073_741_824.0 * 10.0).round() / 10.0)
                .unwrap_or(0.0);

            (gpu_name, vram)
        }
        #[cfg(target_os = "linux")]
        {
            // Try nvidia-smi for discrete GPU name + VRAM
            let nvidia_data = Command::new("nvidia-smi")
                .args(["--query-gpu=name,memory.total", "--format=csv,noheader,nounits"])
                .output()
                .ok()
                .and_then(|o| {
                    if !o.status.success() { return None; }
                    let s = String::from_utf8_lossy(&o.stdout).trim().to_string();
                    let first_line = s.lines().next()?;
                    let parts: Vec<&str> = first_line.split(',').collect();
                    if parts.len() >= 2 {
                        let name = parts[0].trim().to_string();
                        let mb = parts[1].trim().parse::<f64>().ok()?;
                        let gb = (mb / 1024.0 * 10.0).round() / 10.0;
                        Some((name, gb))
                    } else {
                        None
                    }
                });

            if let Some(data) = nvidia_data {
                data
            } else {
                // Fallback: lspci for name, 0 for VRAM
                let gpu_name = Command::new("lspci")
                    .output()
                    .ok()
                    .and_then(|o| {
                        let s = String::from_utf8_lossy(&o.stdout).to_string();
                        s.lines()
                            .find(|l| l.contains("VGA") || l.contains("3D"))
                            .map(|l| l.to_string())
                    })
                    .unwrap_or_else(|| "Unknown".into());
                (gpu_name, 0.0)
            }
        }
    };

    SystemInfo {
        ram_gb,
        vram_gb,
        gpu,
        os: std::env::consts::OS.to_string(),
        arch: std::env::consts::ARCH.to_string(),
    }
}

/// Check if Python is installed, return version string.
#[tauri::command]
fn check_python() -> Option<String> {
    let cmds = if cfg!(target_os = "windows") {
        vec!["python", "python3"]
    } else {
        vec!["python3", "python"]
    };
    for cmd in cmds {
        if let Ok(output) = Command::new(cmd).arg("--version").output() {
            if output.status.success() {
                let version = String::from_utf8_lossy(&output.stdout).trim().to_string();
                if !version.is_empty() {
                    return Some(version);
                }
                // Some pythons print to stderr
                let ver2 = String::from_utf8_lossy(&output.stderr).trim().to_string();
                if !ver2.is_empty() {
                    return Some(ver2);
                }
            }
        }
    }
    None
}

/// Check if Node.js is installed, return version string.
#[tauri::command]
fn check_node() -> Option<String> {
    Command::new("node")
        .arg("--version")
        .output()
        .ok()
        .filter(|o| o.status.success())
        .map(|o| String::from_utf8_lossy(&o.stdout).trim().to_string())
}

/// Install Python via system package manager.
#[tauri::command]
async fn install_python() -> Result<(), String> {
    let status = if cfg!(target_os = "windows") {
        Command::new("winget")
            .args([
                "install",
                "Python.Python.3.12",
                "--accept-package-agreements",
                "--accept-source-agreements",
            ])
            .status()
    } else if cfg!(target_os = "macos") {
        Command::new("brew")
            .args(["install", "python@3.12"])
            .status()
    } else {
        Command::new("sudo")
            .args(["apt-get", "install", "-y", "python3", "python3-pip"])
            .status()
    };

    match status {
        Ok(s) if s.success() => Ok(()),
        Ok(s) => Err(format!("Python install exited with code {:?}", s.code())),
        Err(e) => Err(format!("Failed to run installer: {}", e)),
    }
}

/// Install Node.js via system package manager.
#[tauri::command]
async fn install_node() -> Result<(), String> {
    let status = if cfg!(target_os = "windows") {
        Command::new("winget")
            .args([
                "install",
                "OpenJS.NodeJS.LTS",
                "--accept-package-agreements",
                "--accept-source-agreements",
            ])
            .status()
    } else if cfg!(target_os = "macos") {
        Command::new("brew").args(["install", "node@20"]).status()
    } else {
        Command::new("sudo")
            .args(["apt-get", "install", "-y", "nodejs", "npm"])
            .status()
    };

    match status {
        Ok(s) if s.success() => Ok(()),
        Ok(s) => Err(format!("Node install exited with code {:?}", s.code())),
        Err(e) => Err(format!("Failed to run installer: {}", e)),
    }
}

/// Clone the Fireside repo to the target directory.
#[tauri::command]
async fn clone_repo(fireside_dir: String) -> Result<(), String> {
    let dir = PathBuf::from(&fireside_dir);
    if dir.join("bifrost.py").exists() {
        return Ok(()); // Already cloned
    }

    let status = Command::new("git")
        .args([
            "clone",
            "https://github.com/JordanFableFur/valhalla-mesh.git",
            &fireside_dir,
        ])
        .status()
        .map_err(|e| format!("git clone failed: {}", e))?;

    if status.success() {
        Ok(())
    } else {
        Err(format!("git clone exited with code {:?}", status.code()))
    }
}

/// Install Python + Node dependencies.
#[tauri::command]
async fn install_deps(fireside_dir: String) -> Result<(), String> {
    let dir = PathBuf::from(&fireside_dir);

    // pip install
    let pip_cmd = if cfg!(target_os = "windows") {
        "pip"
    } else {
        "pip3"
    };
    let pip = Command::new(pip_cmd)
        .args(["install", "-r", "requirements.txt"])
        .current_dir(&dir)
        .status()
        .map_err(|e| format!("pip install failed: {}", e))?;

    if !pip.success() {
        return Err("pip install exited with non-zero code".into());
    }

    // npm install for dashboard
    let dashboard_dir = dir.join("dashboard");
    if dashboard_dir.exists() {
        let npm = Command::new("npm")
            .args(["install"])
            .current_dir(&dashboard_dir)
            .status()
            .map_err(|e| format!("npm install failed: {}", e))?;

        if !npm.success() {
            return Err("npm install exited with non-zero code".into());
        }
    }

    Ok(())
}

/// Write all config files (same output as install.sh).
#[tauri::command]
fn write_config(config: FiresideConfig) -> Result<(), String> {
    let home = dirs::home_dir().ok_or("Cannot find home directory")?;
    let fireside_dir = home.join(".fireside");
    let valhalla_dir = home.join(".valhalla");

    // Ensure directories exist
    fs::create_dir_all(&fireside_dir).map_err(|e| e.to_string())?;
    fs::create_dir_all(&valhalla_dir).map_err(|e| e.to_string())?;

    // valhalla.yaml
    let yaml = format!(
        r#"node:
  name: {user}'s-fireside
  role: orchestrator

models:
  providers: {{}}
  aliases:
    default: local/{brain}
  active:
    brain: {brain}
    model: {model}

plugins:
  enabled:
    - model-switch
    - watchdog
    - event-bus
    - working-memory
    - pipeline
    - consumer-api
    - brain-installer
    - companion
    - browse
    - personality

agent:
  name: "{agent_name}"
  style: "{agent_style}"

companion:
  species: {species}
  name: "{companion_name}"
  owner: "{user}"

pipeline:
  git_branching: false
"#,
        user = config.user_name,
        brain = config.brain,
        model = config.model,
        agent_name = config.agent_name,
        agent_style = config.agent_style,
        species = config.companion_species,
        companion_name = config.companion_name,
    );
    fs::write(fireside_dir.join("valhalla.yaml"), &yaml).map_err(|e| e.to_string())?;

    // companion_state.json
    let now = chrono::Utc::now().format("%Y-%m-%dT%H:%M:%SZ").to_string();
    let state = format!(
        r#"{{
  "species": "{species}",
  "name": "{companion_name}",
  "owner": "{user}",
  "agent": {{
    "name": "{agent_name}",
    "style": "{agent_style}"
  }},
  "happiness": 80,
  "xp": 0,
  "level": 1,
  "streak": 0,
  "brain": "{brain}",
  "version": "1.0.0",
  "born": "{now}"
}}"#,
        species = config.companion_species,
        companion_name = config.companion_name,
        user = config.user_name,
        agent_name = config.agent_name,
        agent_style = config.agent_style,
        brain = config.brain,
        now = now,
    );
    fs::write(valhalla_dir.join("companion_state.json"), &state).map_err(|e| e.to_string())?;

    // onboarding.json
    let onboarding = format!(
        r#"{{
  "onboarded": true,
  "user_name": "{user}",
  "personality": "friendly",
  "brain": "{brain}",
  "agent": {{
    "name": "{agent_name}",
    "style": "{agent_style}"
  }},
  "companion": {{
    "species": "{species}",
    "name": "{companion_name}"
  }},
  "installed_at": "{now}"
}}"#,
        user = config.user_name,
        brain = config.brain,
        agent_name = config.agent_name,
        agent_style = config.agent_style,
        species = config.companion_species,
        companion_name = config.companion_name,
        now = now,
    );
    fs::write(fireside_dir.join("onboarding.json"), &onboarding).map_err(|e| e.to_string())?;

    Ok(())
}

/// Start the Fireside backend + dashboard as background processes.
#[tauri::command]
async fn start_fireside(fireside_dir: String) -> Result<(), String> {
    let dir = PathBuf::from(&fireside_dir);

    // Start bifrost.py
    let python_cmd = if cfg!(target_os = "windows") {
        "python"
    } else {
        "python3"
    };
    Command::new(python_cmd)
        .args(["bifrost.py"])
        .current_dir(&dir)
        .spawn()
        .map_err(|e| format!("Failed to start backend: {}", e))?;

    // Start dashboard
    let dashboard_dir = dir.join("dashboard");
    if dashboard_dir.exists() {
        Command::new("npm")
            .args(["run", "dev"])
            .current_dir(&dashboard_dir)
            .spawn()
            .map_err(|e| format!("Failed to start dashboard: {}", e))?;
    }

    Ok(())
}

// ---------------------------------------------------------------------------
// T1 — Backend auto-start + lifecycle management
// ---------------------------------------------------------------------------

use std::sync::{Arc, Mutex};
use std::thread;
use std::process::Child;

struct BackendState {
    child: Option<Child>,
    restart_count: u32,
    running: bool,
}

/// Check if the backend is reachable.
#[tauri::command]
fn get_backend_status() -> serde_json::Value {
    let result = std::net::TcpStream::connect_timeout(
        &"127.0.0.1:8765".parse().unwrap(),
        std::time::Duration::from_millis(500),
    );
    serde_json::json!({
        "running": result.is_ok(),
        "port": 8765,
    })
}

fn spawn_backend(fireside_dir: &PathBuf) -> Option<Child> {
    let python_cmd = if cfg!(target_os = "windows") {
        "python"
    } else {
        "python3"
    };

    match Command::new(python_cmd)
        .args(["bifrost.py"])
        .current_dir(fireside_dir)
        .spawn()
    {
        Ok(child) => {
            println!("[fireside] Backend started (PID: {:?})", child.id());
            Some(child)
        }
        Err(e) => {
            eprintln!("[fireside] Failed to start backend: {}", e);
            None
        }
    }
}

// ---------------------------------------------------------------------------
// Sprint 21 — Brain download + connection test
// ---------------------------------------------------------------------------

/// Download a brain model GGUF from HuggingFace CDN.
/// Returns progress updates; frontend polls or waits for completion.
#[tauri::command]
async fn download_brain(model: String, dest: String) -> Result<String, String> {
    let models = std::collections::HashMap::from([
        ("llama-3.1-8b-q6".to_string(), (
            "bartowski/Meta-Llama-3.1-8B-Instruct-GGUF",
            "Meta-Llama-3.1-8B-Instruct-Q6_K.gguf",
        )),
        ("qwen-2.5-35b-q4".to_string(), (
            "bartowski/Qwen2.5-Coder-32B-Instruct-GGUF",
            "Qwen2.5-Coder-32B-Instruct-Q4_K_M.gguf",
        )),
    ]);

    let (repo, filename) = models.get(&model)
        .ok_or_else(|| format!("Unknown model: {}", model))?;

    let dest_dir = PathBuf::from(&dest);
    fs::create_dir_all(&dest_dir).map_err(|e| format!("Cannot create dir: {}", e))?;
    let target = dest_dir.join(filename);

    // Already downloaded?
    if target.exists() {
        let size = fs::metadata(&target).map(|m| m.len()).unwrap_or(0);
        if size > 100_000_000 {
            return Ok(format!("already_installed:{}", filename));
        }
    }

    // Download via curl/wget (available on all platforms)
    let url = format!("https://huggingface.co/{}/resolve/main/{}", repo, filename);

    let status = if cfg!(target_os = "windows") {
        Command::new("powershell")
            .args(["-NoProfile", "-Command", &format!(
                "Invoke-WebRequest -Uri '{}' -OutFile '{}' -UseBasicParsing",
                url, target.display()
            )])
            .status()
    } else {
        Command::new("curl")
            .args(["-L", "-o", &target.to_string_lossy(), &url])
            .status()
    };

    match status {
        Ok(s) if s.success() => Ok(format!("downloaded:{}", filename)),
        Ok(s) => Err(format!("Download exited with code {:?}", s.code())),
        Err(e) => Err(format!("Download failed: {}", e)),
    }
}

/// Test that the backend is reachable and can respond to a health check.
#[tauri::command]
async fn test_connection() -> Result<String, String> {
    // Give backend a moment to start
    let max_attempts = 10;
    for attempt in 1..=max_attempts {
        match std::net::TcpStream::connect("127.0.0.1:8765") {
            Ok(_) => {
                // TCP connected — now try HTTP health check
                let output = if cfg!(target_os = "windows") {
                    Command::new("powershell")
                        .args(["-NoProfile", "-Command",
                            "(Invoke-WebRequest -Uri 'http://127.0.0.1:8765/api/v1/status/agent' -UseBasicParsing).Content"])
                        .output()
                } else {
                    Command::new("curl")
                        .args(["-s", "http://127.0.0.1:8765/api/v1/status/agent"])
                        .output()
                };

                match output {
                    Ok(o) if o.status.success() => {
                        let body = String::from_utf8_lossy(&o.stdout).to_string();
                        return Ok(format!("connected:{}", body.trim()));
                    }
                    _ => {} // TCP up but HTTP not ready, retry
                }
            }
            Err(_) => {} // Not listening yet
        }

        if attempt < max_attempts {
            std::thread::sleep(std::time::Duration::from_secs(1));
        }
    }

    Err("Backend did not respond after 10 seconds".into())
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

fn main() {
    let backend_state = Arc::new(Mutex::new(BackendState {
        child: None,
        restart_count: 0,
        running: false,
    }));

    let state_for_setup = backend_state.clone();
    let state_for_exit = backend_state.clone();

    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .invoke_handler(tauri::generate_handler![
            get_system_info,
            check_python,
            check_node,
            install_python,
            install_node,
            clone_repo,
            install_deps,
            write_config,
            start_fireside,
            get_backend_status,
            download_brain,
            test_connection,
        ])
        .setup(move |_app| {
            // Auto-start backend if ~/.fireside exists
            let home = dirs::home_dir().unwrap_or_default();
            let fireside_dir = home.join(".fireside");

            if fireside_dir.join("bifrost.py").exists()
                || fireside_dir.join("valhalla.yaml").exists()
            {
                // Find the repo directory (could be ~/.fireside or the dev directory)
                let repo_dir = if fireside_dir.join("bifrost.py").exists() {
                    fireside_dir.clone()
                } else {
                    // Dev mode: look relative to the executable
                    std::env::current_dir().unwrap_or(fireside_dir.clone())
                };

                let state = state_for_setup.clone();
                let dir = repo_dir.clone();

                thread::spawn(move || {
                    // Give the window a moment to render
                    thread::sleep(std::time::Duration::from_millis(2000));

                    let max_restarts = 3;

                    loop {
                        let child = spawn_backend(&dir);
                        if let Some(child) = child {
                            {
                                let mut s = state.lock().unwrap();
                                s.running = true;
                                s.child = Some(child);
                            }

                            // Wait for process to exit via polling
                            loop {
                                let mut s = state.lock().unwrap();
                                if let Some(ref mut c) = s.child {
                                    match c.try_wait() {
                                        Ok(Some(status)) => {
                                            println!("[fireside] Backend exited: {}", status);
                                            s.child = None;
                                            break;
                                        }
                                        Ok(None) => {
                                            // Process is still running
                                        }
                                        Err(e) => {
                                            eprintln!("[fireside] Backend wait error: {}", e);
                                            s.child = None;
                                            break;
                                        }
                                    }
                                } else {
                                    // Process was deleted (e.g., by exit handler)
                                    break;
                                }
                                drop(s);
                                thread::sleep(std::time::Duration::from_millis(500));
                            }

                            let mut s = state.lock().unwrap();
                            s.running = false;
                            s.restart_count += 1;

                            if s.restart_count > max_restarts {
                                eprintln!(
                                    "[fireside] Backend crashed {} times, giving up",
                                    s.restart_count
                                );
                                break;
                            }

                            println!(
                                "[fireside] Restarting backend (attempt {}/{})",
                                s.restart_count, max_restarts
                            );
                            drop(s);

                            // Brief delay before restart
                            thread::sleep(std::time::Duration::from_secs(2));
                        } else {
                            eprintln!("[fireside] Could not spawn backend, aborting");
                            break;
                        }
                    }
                });
            }

            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("error while building Fireside")
        .run(move |_app_handle, event| {
            // Kill backend on app exit
            if let tauri::RunEvent::Exit = event {
                println!("[fireside] App exiting, cleaning up backend...");
                if let Ok(mut s) = state_for_exit.lock() {
                    if let Some(ref mut child) = s.child {
                        let _ = child.kill();
                        println!("[fireside] Backend process killed");
                    }
                    s.running = false;
                }
            }
        });
}
