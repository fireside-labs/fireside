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

    let gpu = {
        #[cfg(target_os = "windows")]
        {
            Command::new("powershell")
                .args(["-NoProfile", "-Command",
                    "(Get-CimInstance Win32_VideoController | Select-Object -First 1).Name"])
                .output()
                .ok()
                .map(|o| String::from_utf8_lossy(&o.stdout).trim().to_string())
                .filter(|s| !s.is_empty())
                .unwrap_or_else(|| "Unknown".into())
        }
        #[cfg(target_os = "macos")]
        {
            Command::new("system_profiler")
                .args(["SPDisplaysDataType"])
                .output()
                .ok()
                .and_then(|o| {
                    let s = String::from_utf8_lossy(&o.stdout).to_string();
                    s.lines()
                        .find(|l| l.contains("Chipset Model:"))
                        .map(|l| l.split(':').nth(1).unwrap_or("Unknown").trim().to_string())
                })
                .unwrap_or_else(|| "Unknown".into())
        }
        #[cfg(target_os = "linux")]
        {
            Command::new("lspci")
                .output()
                .ok()
                .and_then(|o| {
                    let s = String::from_utf8_lossy(&o.stdout).to_string();
                    s.lines()
                        .find(|l| l.contains("VGA") || l.contains("3D"))
                        .map(|l| l.to_string())
                })
                .unwrap_or_else(|| "Unknown".into())
        }
    };

    // Detect VRAM (GPU memory)
    let vram_gb = {
        #[cfg(target_os = "windows")]
        {
            // Try nvidia-smi first (accurate, no 4GB uint32 overflow)
            let nvidia_vram = Command::new("nvidia-smi")
                .args(["--query-gpu=memory.total", "--format=csv,noheader,nounits"])
                .output()
                .ok()
                .and_then(|o| {
                    let s = String::from_utf8_lossy(&o.stdout).trim().to_string();
                    // nvidia-smi returns MB, e.g. "32607"
                    s.lines().next()
                        .and_then(|line| line.trim().parse::<f64>().ok())
                        .map(|mb| (mb / 1024.0 * 10.0).round() / 10.0)
                });

            nvidia_vram.unwrap_or_else(|| {
                // Fallback: WMI AdapterRAM (uint32, overflows above 4GB)
                Command::new("powershell")
                    .args(["-NoProfile", "-Command",
                        "(Get-CimInstance Win32_VideoController | Select-Object -First 1).AdapterRAM"])
                    .output()
                    .ok()
                    .and_then(|o| {
                        let s = String::from_utf8_lossy(&o.stdout).trim().to_string();
                        s.parse::<f64>().ok()
                    })
                    .map(|b| (b / 1_073_741_824.0 * 10.0).round() / 10.0)
                    .unwrap_or(0.0)
            })
        }
        #[cfg(target_os = "macos")]
        {
            // Apple Silicon: unified memory IS the GPU memory
            Command::new("sysctl")
                .args(["-n", "hw.memsize"])
                .output()
                .ok()
                .and_then(|o| {
                    let s = String::from_utf8_lossy(&o.stdout).trim().to_string();
                    s.parse::<f64>().ok()
                })
                .map(|b| (b / 1_073_741_824.0 * 10.0).round() / 10.0)
                .unwrap_or(0.0)
        }
        #[cfg(target_os = "linux")]
        {
            // Try nvidia-smi for discrete GPU VRAM
            Command::new("nvidia-smi")
                .args(["--query-gpu=memory.total", "--format=csv,noheader,nounits"])
                .output()
                .ok()
                .and_then(|o| {
                    if o.status.success() {
                        let s = String::from_utf8_lossy(&o.stdout).trim().to_string();
                        // nvidia-smi returns MiB
                        s.lines().next()
                            .and_then(|l| l.trim().parse::<f64>().ok())
                            .map(|mb| (mb / 1024.0 * 10.0).round() / 10.0)
                    } else {
                        None
                    }
                })
                .unwrap_or(0.0)
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
// Main
// ---------------------------------------------------------------------------

fn main() {
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
        ])
        .run(tauri::generate_context!())
        .expect("error while running Fireside");
}
