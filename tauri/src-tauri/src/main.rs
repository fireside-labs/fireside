// Fireside Desktop — Tauri v2 entry point
// Native installer wizard + backend launcher.

#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use serde::Serialize;
use tauri::Emitter;
use std::fs;
use std::path::PathBuf;
use std::process::Command;
#[cfg(windows)]
use std::os::windows::process::CommandExt;

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/// Create a Command that won't show a console window on Windows.
/// Use this EVERYWHERE instead of `silent_cmd()` directly.
fn silent_cmd(program: &str) -> Command {
    let mut cmd = Command::new(program);
    #[cfg(windows)]
    cmd.creation_flags(0x08000000); // CREATE_NO_WINDOW
    cmd
}

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
            let output = silent_cmd("powershell")
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
            let output = silent_cmd("sysctl").args(["-n", "hw.memsize"]).output();
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
            let nvidia_data = silent_cmd(nvsmi_path)
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
                let wmi_data = silent_cmd("powershell")
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
            let gpu_name = silent_cmd("system_profiler")
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

            let vram = silent_cmd("sysctl")
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
            let nvidia_data = silent_cmd("nvidia-smi")
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
                let gpu_name = silent_cmd("lspci")
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
        if let Ok(output) = silent_cmd(cmd).arg("--version").output() {
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
    silent_cmd("node")
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
        silent_cmd("winget")
            .args([
                "install",
                "Python.Python.3.12",
                "--accept-package-agreements",
                "--accept-source-agreements",
            ])
            .status()
    } else if cfg!(target_os = "macos") {
        silent_cmd("brew")
            .args(["install", "python@3.12"])
            .status()
    } else {
        silent_cmd("sudo")
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
        silent_cmd("winget")
            .args([
                "install",
                "OpenJS.NodeJS.LTS",
                "--accept-package-agreements",
                "--accept-source-agreements",
            ])
            .status()
    } else if cfg!(target_os = "macos") {
        silent_cmd("brew").args(["install", "node@20"]).status()
    } else {
        silent_cmd("sudo")
            .args(["apt-get", "install", "-y", "nodejs", "npm"])
            .status()
    };

    match status {
        Ok(s) if s.success() => Ok(()),
        Ok(s) => Err(format!("Node install exited with code {:?}", s.code())),
        Err(e) => Err(format!("Failed to run installer: {}", e)),
    }
}

/// Check if Tailscale is installed and connected.
#[tauri::command]
fn check_tailscale() -> serde_json::Value {
    // Check if tailscale CLI exists
    let installed = if cfg!(target_os = "windows") {
        silent_cmd("where").arg("tailscale").output()
            .map(|o| o.status.success()).unwrap_or(false)
    } else {
        silent_cmd("which").arg("tailscale").output()
            .map(|o| o.status.success()).unwrap_or(false)
    };

    if !installed {
        return serde_json::json!({
            "installed": false,
            "connected": false,
            "ip": null
        });
    }

    // Check status
    let status = silent_cmd("tailscale")
        .args(["status", "--json"])
        .output();

    let connected = match &status {
        Ok(o) if o.status.success() => {
            let s = String::from_utf8_lossy(&o.stdout);
            s.contains("Running")
        }
        _ => false,
    };

    // Get IP
    let ip = silent_cmd("tailscale").args(["ip", "-4"]).output()
        .ok()
        .filter(|o| o.status.success())
        .map(|o| String::from_utf8_lossy(&o.stdout).trim().to_string());

    serde_json::json!({
        "installed": true,
        "connected": connected,
        "ip": ip
    })
}

/// Install Tailscale silently via system package manager.
#[tauri::command]
async fn install_tailscale() -> Result<String, String> {
    let status = if cfg!(target_os = "windows") {
        silent_cmd("winget")
            .args([
                "install",
                "Tailscale.Tailscale",
                "--accept-package-agreements",
                "--accept-source-agreements",
                "--silent",
            ])
            .status()
    } else if cfg!(target_os = "macos") {
        silent_cmd("brew")
            .args(["install", "--cask", "tailscale"])
            .status()
    } else {
        // Linux: use the official install script
        silent_cmd("sh")
            .args(["-c", "curl -fsSL https://tailscale.com/install.sh | sh"])
            .status()
    };

    match status {
        Ok(s) if s.success() => Ok("installed".into()),
        Ok(s) => Err(format!("Tailscale install exited with code {:?}", s.code())),
        Err(e) => Err(format!("Failed to install Tailscale: {}", e)),
    }
}

/// Connect Tailscale with an auth key (for OAuth flow).
#[tauri::command]
async fn connect_tailscale(auth_key: String, hostname: String) -> Result<String, String> {
    let status = silent_cmd("tailscale")
        .args(["up", &format!("--authkey={}", auth_key), &format!("--hostname={}", hostname), "--accept-routes"])
        .status()
        .map_err(|e| format!("tailscale up failed: {}", e))?;

    if !status.success() {
        return Err(format!("tailscale up exited with code {:?}", status.code()));
    }

    // Get the assigned IP
    std::thread::sleep(std::time::Duration::from_secs(3));
    let ip = silent_cmd("tailscale").args(["ip", "-4"]).output()
        .ok()
        .filter(|o| o.status.success())
        .map(|o| String::from_utf8_lossy(&o.stdout).trim().to_string())
        .unwrap_or_default();

    Ok(ip)
}

/// Clone the Fireside repo to the target directory.
#[tauri::command]
async fn clone_repo(fireside_dir: String) -> Result<(), String> {
    let dir = PathBuf::from(&fireside_dir);

    // Already have the repo? Just pull latest
    if dir.join("bifrost.py").exists() {
        println!("[fireside] Repo already present, pulling latest...");
        let _ = silent_cmd("git")
            .args(["pull", "--ff-only"])
            .current_dir(&dir)
            .status();
        return Ok(());
    }

    fs::create_dir_all(&dir).map_err(|e| format!("Cannot create {}: {}", fireside_dir, e))?;

    // Backup existing user config files (write_config creates these BEFORE clone_repo)
    let config_files = ["valhalla.yaml", "keys.json", "onboarding.json", "guardian_stats.json"];
    let mut backups: Vec<(String, Vec<u8>)> = Vec::new();
    for f in &config_files {
        let path = dir.join(f);
        if path.exists() {
            if let Ok(data) = fs::read(&path) {
                backups.push((f.to_string(), data));
                let _ = fs::remove_file(&path);
                println!("[fireside] Backed up {}", f);
            }
        }
    }

    if !dir.join(".git").exists() {
        // Init fresh repo (can't use git clone — dir has models/, bin/, etc.)
        println!("[fireside] Initializing repo in existing directory...");
        let _ = silent_cmd("git").args(["init"]).current_dir(&dir).status();
        let _ = silent_cmd("git")
            .args(["remote", "add", "origin", "https://github.com/JordanFableFur/valhalla-mesh.git"])
            .current_dir(&dir).status();
    }

    // Fetch latest and force checkout (safe — user configs are backed up above)
    println!("[fireside] Fetching and checking out latest code...");
    let _ = silent_cmd("git").args(["fetch", "origin"]).current_dir(&dir).status();
    let _ = silent_cmd("git")
        .args(["checkout", "-f", "origin/main", "-B", "main"])
        .current_dir(&dir).status();

    // Restore user config files (overwrite repo defaults with user's versions)
    for (name, data) in &backups {
        let path = dir.join(name);
        if let Err(e) = fs::write(&path, data) {
            eprintln!("[fireside] Failed to restore {}: {}", name, e);
        } else {
            println!("[fireside] Restored user config: {}", name);
        }
    }

    if dir.join("bifrost.py").exists() {
        Ok(())
    } else {
        Err("Repository clone completed but bifrost.py not found".into())
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
    let pip = silent_cmd(pip_cmd)
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
        let npm = silent_cmd("npm")
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
    - guardian
    - social

agent:
  name: "{agent_name}"
  style: "{agent_style}"

companion:
  species: {species}
  name: "{companion_name}"
  owner: "{user}"

network:
  tailscale_ip: ""
  tailscale_hostname: ""

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
    silent_cmd(python_cmd)
        .args(["bifrost.py"])
        .current_dir(&dir)
        .spawn()
        .map_err(|e| format!("Failed to start backend: {}", e))?;

    // Start dashboard
    let dashboard_dir = dir.join("dashboard");
    if dashboard_dir.exists() {
        silent_cmd("npm")
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

/// Restart the Python backend (bifrost.py) so it picks up a newly downloaded model.
/// Kills the old process if running, then spawns a fresh one.
#[tauri::command]
fn restart_backend(state: tauri::State<'_, Arc<Mutex<BackendState>>>) -> Result<String, String> {
    let home = dirs::home_dir().ok_or("Cannot find home directory")?;
    let fireside_dir = home.join(".fireside");

    // Find the repo directory
    let repo_dir = if fireside_dir.join("bifrost.py").exists() {
        fireside_dir
    } else {
        // Dev mode: try current dir or parent dirs
        let cwd = std::env::current_dir().unwrap_or(fireside_dir.clone());
        if cwd.join("bifrost.py").exists() {
            cwd
        } else if cwd.join("..").join("bifrost.py").exists() {
            cwd.join("..").canonicalize().unwrap_or(fireside_dir)
        } else {
            return Err("bifrost.py not found in ~/.fireside or current directory".into());
        }
    };

    // Kill existing backend
    {
        let mut s = state.lock().map_err(|e| format!("Lock error: {}", e))?;
        if let Some(ref mut child) = s.child {
            println!("[fireside] Killing old backend (pid={:?})", child.id());
            let _ = child.kill();
            let _ = child.wait();
        }
        s.child = None;
        s.running = false;
        s.restart_count = 0;
    }

    // Brief delay to let port free up
    thread::sleep(std::time::Duration::from_millis(500));

    // Spawn new backend
    match spawn_backend(&repo_dir) {
        Some(child) => {
            let pid = child.id();
            let mut s = state.lock().map_err(|e| format!("Lock error: {}", e))?;
            s.child = Some(child);
            s.running = true;
            println!("[fireside] Backend restarted (pid={:?})", pid);
            Ok(format!("Backend restarted (pid={:?})", pid))
        }
        None => Err("Failed to spawn backend process".into()),
    }
}

fn spawn_backend(fireside_dir: &PathBuf) -> Option<Child> {
    let python_cmd = if cfg!(target_os = "windows") {
        "python"
    } else {
        "python3"
    };

    match silent_cmd(python_cmd)
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

/// Start llama-server directly with the newest downloaded GGUF model.
/// This bypasses the Python backend entirely — chat goes directly to llama-server.
#[tauri::command]
fn start_llama_server(state: tauri::State<'_, Arc<Mutex<BackendState>>>) -> Result<String, String> {
    let home = dirs::home_dir().ok_or("Cannot find home directory")?;
    let models_dir = home.join(".fireside").join("models");

    // Find the newest GGUF file
    let mut ggufs: Vec<_> = fs::read_dir(&models_dir)
        .map_err(|e| format!("Cannot read models dir: {}", e))?
        .filter_map(|e| e.ok())
        .filter(|e| e.path().extension().map_or(false, |ext| ext == "gguf"))
        .collect();

    ggufs.sort_by_key(|e| std::cmp::Reverse(e.metadata().map(|m| m.modified().unwrap_or(std::time::SystemTime::UNIX_EPOCH)).unwrap_or(std::time::SystemTime::UNIX_EPOCH)));

    let gguf = ggufs.first().ok_or("No GGUF models found in ~/.fireside/models/")?;
    let model_path = gguf.path();

    // Find llama-server binary
    let binary = find_llama_server()
        .ok_or("llama-server not found. Please install llama.cpp or place llama-server.exe in PATH.")?;

    // Kill any existing backend/llama-server
    {
        let mut s = state.lock().map_err(|e| format!("Lock error: {}", e))?;
        if let Some(ref mut child) = s.child {
            let _ = child.kill();
            let _ = child.wait();
        }
        s.child = None;
        s.running = false;
    }

    thread::sleep(std::time::Duration::from_millis(300));

    // Start llama-server with full GPU offloading
    let mut cmd_args = vec![
        "--model".to_string(), model_path.to_string_lossy().to_string(),
        "--port".to_string(), "8080".to_string(),
        "--host".to_string(), "127.0.0.1".to_string(),
        "--ctx-size".to_string(), "8192".to_string(),
        "--n-gpu-layers".to_string(), "99".to_string(),
        "--flash-attn".to_string(), "on".to_string(),
    ];

    // Disable thinking for small models (< 3B) — they waste tokens on garbage thoughts
    let model_name = model_path.file_name().unwrap_or_default().to_string_lossy().to_lowercase();
    let is_small = model_name.contains("0.6b") || model_name.contains("0.5b")
        || model_name.contains("1b") || model_name.contains("1.5b")
        || model_name.contains("2b");
    if is_small {
        println!("[fireside] Small model detected, disabling thinking mode");
        cmd_args.push("--reasoning-budget".to_string());
        cmd_args.push("0".to_string());
    }

    println!("[fireside] Starting llama-server: {} {}", binary, cmd_args.join(" "));

    match silent_cmd(&binary)
        .args(&cmd_args)
        .spawn()
    {
        Ok(child) => {
            let pid = child.id();
            let mut s = state.lock().map_err(|e| format!("Lock error: {}", e))?;
            s.child = Some(child);
            s.running = true;
            let msg = format!("llama-server started (pid={:?}) with {}", pid, model_path.file_name().unwrap_or_default().to_string_lossy());
            println!("[fireside] {}", msg);
            Ok(msg)
        }
        Err(e) => Err(format!("Failed to start llama-server: {}", e)),
    }
}

fn find_llama_server() -> Option<String> {
    let exe = if cfg!(target_os = "windows") { "llama-server.exe" } else { "llama-server" };

    // 1. Canonical location: ~/.fireside/bin/ (installed by the installer)
    let home = dirs::home_dir().unwrap_or_default();
    let canonical = home.join(".fireside").join("bin").join(exe);
    if canonical.exists() {
        return Some(canonical.to_string_lossy().to_string());
    }

    // 2. Also check nested inside extracted zip (llama.cpp zips have subdirs)
    let bin_dir = home.join(".fireside").join("bin");
    if bin_dir.exists() {
        for entry in walkdir_find_exe(&bin_dir, exe) {
            return Some(entry);
        }
    }

    // 3. Try system PATH
    if let Ok(output) = silent_cmd(if cfg!(target_os = "windows") { "where" } else { "which" })
        .arg("llama-server")
        .output()
    {
        if output.status.success() {
            let path = String::from_utf8_lossy(&output.stdout)
                .lines().next().unwrap_or("").trim().to_string();
            if !path.is_empty() {
                return Some(path);
            }
        }
    }

    None
}

/// Recursively find an exe in a directory (handles zip extraction subdirs)
fn walkdir_find_exe(dir: &PathBuf, exe_name: &str) -> Vec<String> {
    let mut results = Vec::new();
    if let Ok(entries) = fs::read_dir(dir) {
        for entry in entries.filter_map(|e| e.ok()) {
            let path = entry.path();
            if path.is_file() && path.file_name().map_or(false, |n| n == exe_name) {
                results.push(path.to_string_lossy().to_string());
            } else if path.is_dir() {
                results.extend(walkdir_find_exe(&path, exe_name));
            }
        }
    }
    results
}

/// Download llama-server binary from GitHub releases to ~/.fireside/bin/.
/// This is called during installation so new users get everything automatically.
#[tauri::command]
async fn download_llama_server(app: tauri::AppHandle) -> Result<String, String> {
    let home = dirs::home_dir().ok_or("Cannot find home directory")?;
    let bin_dir = home.join(".fireside").join("bin");
    fs::create_dir_all(&bin_dir).map_err(|e| format!("Cannot create bin dir: {}", e))?;

    let exe = if cfg!(target_os = "windows") { "llama-server.exe" } else { "llama-server" };

    // Check if already installed
    if find_llama_server().is_some() {
        return Ok("llama-server already installed".into());
    }

    // Determine download URL based on platform
    let release = "b5460";
    let url = if cfg!(target_os = "windows") {
        format!("https://github.com/ggml-org/llama.cpp/releases/download/{}/llama-{}-bin-win-cuda-cu12.4-x64.zip", release, release)
    } else if cfg!(target_os = "macos") {
        format!("https://github.com/ggml-org/llama.cpp/releases/download/{}/llama-{}-bin-macos-arm64.zip", release, release)
    } else {
        format!("https://github.com/ggml-org/llama.cpp/releases/download/{}/llama-{}-bin-ubuntu-x64.zip", release, release)
    };

    let zip_path = bin_dir.join("llama-server.zip");

    // Emit progress to frontend
    let _ = app.emit("download-progress", DownloadProgress {
        percent: 0.0, downloaded_mb: 0.0, total_mb: 0.0, speed_mbps: 0.0,
        status: "downloading_runtime".to_string(),
    });

    println!("[fireside] Downloading llama-server from {}", url);

    // Download the zip
    let client = reqwest::Client::builder()
        .user_agent("Fireside/1.0 (AI Companion Installer)")
        .build()
        .map_err(|e| format!("HTTP client error: {}", e))?;

    let response = client.get(&url).send().await
        .map_err(|e| format!("Download failed: {}", e))?;

    if !response.status().is_success() {
        return Err(format!("HTTP {}: Download failed", response.status()));
    }

    let bytes = response.bytes().await
        .map_err(|e| format!("Failed to read response: {}", e))?;

    fs::write(&zip_path, &bytes)
        .map_err(|e| format!("Failed to write zip: {}", e))?;

    println!("[fireside] Downloaded {} MB, extracting...", bytes.len() / 1_048_576);

    // Extract the zip
    let file = fs::File::open(&zip_path)
        .map_err(|e| format!("Cannot open zip: {}", e))?;
    let mut archive = zip::ZipArchive::new(file)
        .map_err(|e| format!("Invalid zip: {}", e))?;

    for i in 0..archive.len() {
        let mut entry = archive.by_index(i)
            .map_err(|e| format!("Zip entry error: {}", e))?;

        let name = entry.name().to_string();
        let out_path = bin_dir.join(&name);

        if entry.is_dir() {
            fs::create_dir_all(&out_path).ok();
        } else {
            if let Some(parent) = out_path.parent() {
                fs::create_dir_all(parent).ok();
            }
            let mut outfile = fs::File::create(&out_path)
                .map_err(|e| format!("Cannot create {}: {}", name, e))?;
            std::io::copy(&mut entry, &mut outfile)
                .map_err(|e| format!("Extract error: {}", e))?;
        }
    }

    // Clean up zip
    fs::remove_file(&zip_path).ok();

    // Verify llama-server was extracted
    match find_llama_server() {
        Some(path) => {
            println!("[fireside] llama-server installed at: {}", path);
            let _ = app.emit("download-progress", DownloadProgress {
                percent: 100.0, downloaded_mb: 0.0, total_mb: 0.0, speed_mbps: 0.0,
                status: "runtime_ready".to_string(),
            });
            Ok(format!("llama-server installed: {}", path))
        }
        None => Err(format!("Extraction succeeded but {} not found in {:?}", exe, bin_dir)),
    }
}

// ---------------------------------------------------------------------------
// Sprint 21 — Brain download + connection test
// ---------------------------------------------------------------------------

/// Progress event payload sent to the frontend during model download.
#[derive(Clone, Serialize)]
struct DownloadProgress {
    percent: f64,
    downloaded_mb: f64,
    total_mb: f64,
    speed_mbps: f64,
    status: String, // "downloading", "verifying", "complete", "resuming"
}

/// Download a brain model GGUF from HuggingFace CDN with real progress.
/// `quant` should be one of: "4-bit", "6-bit", "8-bit", "API" (cloud, no download).
#[tauri::command]
async fn download_brain(
    app: tauri::AppHandle,
    model: String,
    quant: String,
    dest: String,
) -> Result<String, String> {
    use futures_util::StreamExt;
    use std::io::Write;

    // Cloud models don't need downloads
    if quant == "API" || model.starts_with("cloud-") {
        return Ok("cloud_model:no_download_needed".to_string());
    }

    // Map user-facing quant labels to GGUF suffixes
    let suffix = match quant.as_str() {
        "4-bit" => "Q4_K_M",
        "6-bit" => "Q6_K",
        "8-bit" => "Q8_0",
        _ => "Q6_K",
    };

    // Each entry: model_id -> (hf_repo, base_filename_without_quant)
    // ALL URLs verified with curl — every one returns HTTP 302 ✓
    let models = std::collections::HashMap::from([
        // ── Speed models (all verified 302) ───────────────────────────────────
        ("phi-3-mini", ("bartowski/Phi-3-mini-4k-instruct-GGUF", "Phi-3-mini-4k-instruct")),
        ("llama-3.1-8b", ("bartowski/Meta-Llama-3.1-8B-Instruct-GGUF", "Meta-Llama-3.1-8B-Instruct")),
        ("llama-3.1-8b-q6", ("bartowski/Meta-Llama-3.1-8B-Instruct-GGUF", "Meta-Llama-3.1-8B-Instruct")),
        ("llama-3.2-3b", ("bartowski/Llama-3.2-3B-Instruct-GGUF", "Llama-3.2-3B-Instruct")),
        ("qwen3-0.6b", ("unsloth/Qwen3-0.6B-GGUF", "Qwen3-0.6B")),
        ("qwen3-1.7b", ("unsloth/Qwen3-1.7B-GGUF", "Qwen3-1.7B")),
        ("qwen3-4b", ("unsloth/Qwen3-4B-GGUF", "Qwen3-4B")),
        ("qwen3-8b", ("unsloth/Qwen3-8B-GGUF", "Qwen3-8B")),
        ("qwen-2.5-7b", ("bartowski/Qwen2.5-7B-Instruct-GGUF", "Qwen2.5-7B-Instruct")),
        ("qwen-3.5-7b", ("unsloth/Qwen3.5-9B-GGUF", "Qwen3.5-9B")),
        ("gemma-2-9b", ("bartowski/gemma-2-9b-it-GGUF", "gemma-2-9b-it")),
        ("mistral-nemo-12b", ("bartowski/Mistral-Nemo-Instruct-2407-GGUF", "Mistral-Nemo-Instruct-2407")),
        ("dolphin-2.9-llama3-8b", ("cognitivecomputations/dolphin-2.9-llama3-8b-gguf", "dolphin-2.9-llama3-8b")),
        ("hermes-3-8b", ("bartowski/Hermes-3-Llama-3.1-8B-GGUF", "Hermes-3-Llama-3.1-8B")),
        // ── Power models (all verified 302) ───────────────────────────────────
        ("qwen3-14b", ("unsloth/Qwen3-14B-GGUF", "Qwen3-14B")),
        ("qwen3-30b-a3b", ("unsloth/Qwen3-30B-A3B-GGUF", "Qwen3-30B-A3B")),
        ("qwen3-32b", ("unsloth/Qwen3-32B-GGUF", "Qwen3-32B")),
        ("qwq-32b", ("bartowski/QwQ-32B-Preview-GGUF", "QwQ-32B-Preview")),
        ("qwen-2.5-32b", ("bartowski/Qwen2.5-32B-Instruct-GGUF", "Qwen2.5-32B-Instruct")),
        ("qwen-2.5-14b", ("bartowski/Qwen2.5-14B-Instruct-GGUF", "Qwen2.5-14B-Instruct")),
        ("gemma-2-27b", ("bartowski/gemma-2-27b-it-GGUF", "gemma-2-27b-it")),
        ("yi-1.5-34b", ("bartowski/Yi-1.5-34B-Chat-GGUF", "Yi-1.5-34B-Chat")),
        ("command-r-35b", ("bartowski/c4ai-command-r-v01-GGUF", "c4ai-command-r-v01")),
        ("llama-3.1-70b", ("bartowski/Meta-Llama-3.1-70B-Instruct-GGUF", "Meta-Llama-3.1-70B-Instruct")),
        ("nemotron-70b", ("bartowski/Llama-3.1-Nemotron-70B-Instruct-HF-GGUF", "Llama-3.1-Nemotron-70B-Instruct-HF")),
        ("glm-4.7-flash", ("unsloth/GLM-4.7-Flash-GGUF", "GLM-4.7-Flash")),
        // ── Specialist models (all verified 302) ──────────────────────────────
        ("qwen3-coder-8b", ("unsloth/Qwen3-Coder-Next-GGUF", "Qwen3-Coder-Next")),
        ("qwen-2.5-coder-32b", ("bartowski/Qwen2.5-Coder-32B-Instruct-GGUF", "Qwen2.5-Coder-32B-Instruct")),
        ("qwen-2.5-coder-14b", ("bartowski/Qwen2.5-Coder-14B-Instruct-GGUF", "Qwen2.5-Coder-14B-Instruct")),
        ("codestral-22b", ("bartowski/Codestral-22B-v0.1-GGUF", "Codestral-22B-v0.1")),
        ("deepseek-coder-v2", ("bartowski/DeepSeek-Coder-V2-Lite-Instruct-GGUF", "DeepSeek-Coder-V2-Lite-Instruct")),
        ("hermes-3-70b", ("bartowski/Hermes-3-Llama-3.1-70B-GGUF", "Hermes-3-Llama-3.1-70B")),
        ("glm-4-9b", ("bartowski/glm-4-9b-chat-GGUF", "glm-4-9b-chat")),
        ("glm-z1-9b", ("bartowski/THUDM_glm-z1-9b-0414-GGUF", "glm-z1-9b-0414")),
        ("pixtral-12b", ("bartowski/mistral-community_pixtral-12b-GGUF", "mistral-community_pixtral-12b")),
    ]);

    let (repo, base) = models.get(model.as_str())
        .ok_or_else(|| format!("Unknown model: {}", model))?;

    let filename = format!("{}-{}.gguf", base, suffix);
    let url = format!("https://huggingface.co/{}/resolve/main/{}", repo, filename);

    // Expand ~ to home directory (PathBuf doesn't do this on Windows)
    let dest_expanded = if dest.starts_with("~/") || dest.starts_with("~\\") {
        let home = dirs::home_dir().ok_or("Cannot find home directory")?;
        home.join(&dest[2..])
    } else {
        PathBuf::from(&dest)
    };
    let dest_dir = dest_expanded;
    fs::create_dir_all(&dest_dir).map_err(|e| format!("Cannot create dir {}: {}", dest_dir.display(), e))?;
    let target = dest_dir.join(&filename);
    let part_file = dest_dir.join(format!("{}.part", filename));

    // Already fully downloaded?
    if target.exists() {
        let size = fs::metadata(&target).map(|m| m.len()).unwrap_or(0);
        if size > 100_000_000 {
            let _ = app.emit("download-progress", DownloadProgress {
                percent: 100.0, downloaded_mb: size as f64 / 1_048_576.0,
                total_mb: size as f64 / 1_048_576.0, speed_mbps: 0.0,
                status: "complete".to_string(),
            });
            return Ok(format!("already_installed:{}", filename));
        }
    }

    // Check for existing partial download (resume support)
    let existing_bytes = if part_file.exists() {
        fs::metadata(&part_file).map(|m| m.len()).unwrap_or(0)
    } else {
        0
    };

    // Build HTTP request with optional Range header for resume
    let client = reqwest::Client::builder()
        .user_agent("Fireside/1.0 (AI Companion Installer)")
        .build()
        .map_err(|e| format!("HTTP client error: {}", e))?;
    let mut request = client.get(&url);
    if existing_bytes > 0 {
        request = request.header("Range", format!("bytes={}-", existing_bytes));
        let _ = app.emit("download-progress", DownloadProgress {
            percent: 0.0, downloaded_mb: existing_bytes as f64 / 1_048_576.0,
            total_mb: 0.0, speed_mbps: 0.0,
            status: "resuming".to_string(),
        });
    }

    let response = request.send().await
        .map_err(|e| format!("HTTP request failed: {}", e))?;

    if !response.status().is_success() && response.status().as_u16() != 206 {
        return Err(format!("HuggingFace returned HTTP {}", response.status()));
    }

    // Calculate total size (from Content-Length + existing bytes)
    let content_length = response.content_length().unwrap_or(0);
    let total_bytes = if existing_bytes > 0 && response.status().as_u16() == 206 {
        content_length + existing_bytes
    } else {
        content_length
    };
    let total_mb = total_bytes as f64 / 1_048_576.0;

    // Open file for writing (append if resuming)
    let mut file = if existing_bytes > 0 && response.status().as_u16() == 206 {
        std::fs::OpenOptions::new().append(true).open(&part_file)
    } else {
        std::fs::File::create(&part_file).map(|f| f)
    }.map_err(|e| format!("Cannot open file for writing: {}", e))?;

    // Stream the download with progress
    let mut downloaded = existing_bytes;
    let mut last_emit = std::time::Instant::now();
    let start_time = std::time::Instant::now();
    let mut stream = response.bytes_stream();

    while let Some(chunk_result) = stream.next().await {
        let chunk = chunk_result.map_err(|e| format!("Download stream error: {}", e))?;
        file.write_all(&chunk).map_err(|e| format!("Write error: {}", e))?;
        downloaded += chunk.len() as u64;

        // Emit progress every 512KB or 500ms (whichever comes first)
        if last_emit.elapsed().as_millis() > 500 || downloaded == total_bytes {
            let elapsed = start_time.elapsed().as_secs_f64().max(0.1);
            let dl_since_start = (downloaded - existing_bytes) as f64;
            let speed_mbps = (dl_since_start / 1_048_576.0) / elapsed;
            let percent = if total_bytes > 0 {
                (downloaded as f64 / total_bytes as f64) * 100.0
            } else {
                0.0
            };

            let _ = app.emit("download-progress", DownloadProgress {
                percent,
                downloaded_mb: downloaded as f64 / 1_048_576.0,
                total_mb,
                speed_mbps,
                status: "downloading".to_string(),
            });
            last_emit = std::time::Instant::now();
        }
    }

    file.flush().map_err(|e| format!("Flush error: {}", e))?;
    drop(file);

    // Verify GGUF magic number (first 4 bytes should be 0x47475546 = "GGUF")
    let _ = app.emit("download-progress", DownloadProgress {
        percent: 99.5, downloaded_mb: total_mb, total_mb,
        speed_mbps: 0.0, status: "verifying".to_string(),
    });

    let magic_ok = std::fs::File::open(&part_file)
        .and_then(|mut f| {
            use std::io::Read;
            let mut buf = [0u8; 4];
            f.read_exact(&mut buf)?;
            Ok(buf)
        })
        .map(|buf| &buf == b"GGUF")
        .unwrap_or(false);

    if !magic_ok {
        let _ = fs::remove_file(&part_file);
        return Err("Downloaded file is not a valid GGUF model. The file may be corrupted or the URL may have changed.".to_string());
    }

    // Rename .part to final filename
    fs::rename(&part_file, &target)
        .map_err(|e| format!("Cannot rename .part file: {}", e))?;

    let _ = app.emit("download-progress", DownloadProgress {
        percent: 100.0, downloaded_mb: total_mb, total_mb,
        speed_mbps: 0.0, status: "complete".to_string(),
    });

    Ok(format!("downloaded:{}", filename))
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
                    silent_cmd("powershell")
                        .args(["-NoProfile", "-Command",
                            "(Invoke-WebRequest -Uri 'http://127.0.0.1:8765/api/v1/status/agent' -UseBasicParsing).Content"])
                        .output()
                } else {
                    silent_cmd("curl")
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
            check_tailscale,
            install_tailscale,
            connect_tailscale,
            clone_repo,
            install_deps,
            write_config,
            start_fireside,
            get_backend_status,
            download_brain,
            test_connection,
            restart_backend,
            start_llama_server,
            download_llama_server,
        ])
        .manage(backend_state.clone())
        .setup(move |_app| {
            // Auto-start backend if ~/.fireside exists
            let home = dirs::home_dir().unwrap_or_default();
            let fireside_dir = home.join(".fireside");
            let models_dir = fireside_dir.join("models");

            // Strategy 1: Python backend (bifrost.py exists)
            if fireside_dir.join("bifrost.py").exists() {
                let state = state_for_setup.clone();
                let dir = fireside_dir.clone();

                thread::spawn(move || {
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

                            loop {
                                let mut s = state.lock().unwrap();
                                if let Some(ref mut c) = s.child {
                                    match c.try_wait() {
                                        Ok(Some(status)) => {
                                            println!("[fireside] Backend exited: {}", status);
                                            s.child = None;
                                            break;
                                        }
                                        Ok(None) => {}
                                        Err(e) => {
                                            eprintln!("[fireside] Backend wait error: {}", e);
                                            s.child = None;
                                            break;
                                        }
                                    }
                                } else {
                                    break;
                                }
                                drop(s);
                                thread::sleep(std::time::Duration::from_millis(500));
                            }

                            let mut s = state.lock().unwrap();
                            s.running = false;
                            s.restart_count += 1;
                            if s.restart_count > max_restarts {
                                eprintln!("[fireside] Backend crashed {} times, giving up", s.restart_count);
                                break;
                            }
                            println!("[fireside] Restarting backend (attempt {}/{})", s.restart_count, max_restarts);
                            drop(s);
                            thread::sleep(std::time::Duration::from_secs(2));
                        } else {
                            eprintln!("[fireside] Could not spawn backend, aborting");
                            break;
                        }
                    }
                });
            }
            // Strategy 2: Direct llama-server (no Python, but GGUF exists)
            else if models_dir.exists() {
                let state = state_for_setup.clone();

                thread::spawn(move || {
                    thread::sleep(std::time::Duration::from_millis(2000));

                    // Find newest GGUF
                    let mut ggufs: Vec<_> = fs::read_dir(&models_dir)
                        .into_iter().flatten().filter_map(|e| e.ok())
                        .filter(|e| e.path().extension().map_or(false, |ext| ext == "gguf"))
                        .collect();

                    if ggufs.is_empty() {
                        println!("[fireside] No GGUF models found, skipping auto-start");
                        return;
                    }

                    ggufs.sort_by_key(|e| std::cmp::Reverse(
                        e.metadata().and_then(|m| m.modified()).unwrap_or(std::time::SystemTime::UNIX_EPOCH)
                    ));

                    let model_path = ggufs[0].path();
                    println!("[fireside] Auto-starting llama-server with {}", model_path.display());

                    // Find llama-server binary
                    let binary = match find_llama_server() {
                        Some(b) => b,
                        None => {
                            eprintln!("[fireside] llama-server not found, cannot auto-start");
                            return;
                        }
                    };

                    // Build args — disable thinking for small models
                    let model_name = model_path.file_name().unwrap_or_default().to_string_lossy().to_lowercase();
                    let is_small = model_name.contains("0.6b") || model_name.contains("0.5b")
                        || model_name.contains("1b") || model_name.contains("1.5b")
                        || model_name.contains("2b");

                    let mut args: Vec<String> = vec![
                        "--model".into(), model_path.to_string_lossy().to_string(),
                        "--port".into(), "8080".into(),
                        "--host".into(), "127.0.0.1".into(),
                        "--ctx-size".into(), "8192".into(),
                        "--n-gpu-layers".into(), "99".into(),
                        "--flash-attn".into(), "on".into(),
                    ];
                    if is_small {
                        println!("[fireside] Small model detected, disabling thinking mode");
                        args.push("--reasoning-budget".into());
                        args.push("0".into());
                    }

                    let child = silent_cmd(&binary)
                        .args(&args)
                        .spawn();

                    match child {
                        Ok(child) => {
                            let pid = child.id();
                            let mut s = state.lock().unwrap();
                            s.child = Some(child);
                            s.running = true;
                            println!("[fireside] llama-server started (pid={:?})", pid);
                        }
                        Err(e) => {
                            eprintln!("[fireside] Failed to start llama-server: {}", e);
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
