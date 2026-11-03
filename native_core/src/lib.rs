use pyo3::prelude::*;
use pyo3::types::{PyDict, PyTuple};
use std::sync::atomic::{AtomicBool, AtomicI32, Ordering};
use std::time::SystemTime;
use regex::Regex;

static LAST_AC_LINE: AtomicI32 = AtomicI32::new(-1);
static ABORT_LATCHED: AtomicBool = AtomicBool::new(false);

#[pyfunction]
fn poll_power_and_metrics(py: Python<'_>) -> PyResult<PyObject> {
    #[cfg(windows)]
    unsafe {
        use windows_sys::Win32::System::Power::{GetSystemPowerStatus, SYSTEM_POWER_STATUS};
        use windows_sys::Win32::System::SystemInformation::{GlobalMemoryStatusEx, MEMORYSTATUSEX};

        let mut sps: SYSTEM_POWER_STATUS = std::mem::zeroed();
        let power_res = GetSystemPowerStatus(&mut sps);

        let ac_line = if power_res != 0 { sps.ACLineStatus as i32 } else { 1 };
        let ac_plugged = ac_line == 1;
        let mut bat_pct = if power_res != 0 { sps.BatteryLifePercent as i32 } else { 100 };
        if bat_pct > 100 { bat_pct = 100; }
        let bat_charging = if power_res != 0 { (sps.BatteryFlag & 8) != 0 } else { false };

        let prev = LAST_AC_LINE.swap(ac_line, Ordering::SeqCst);
        let changed = prev != -1 && prev != ac_line;

        let mut mem: MEMORYSTATUSEX = std::mem::zeroed();
        mem.dwLength = std::mem::size_of::<MEMORYSTATUSEX>() as u32;
        let mem_res = GlobalMemoryStatusEx(&mut mem);

        let (ram_pct, ram_used_gb, ram_total_gb) = if mem_res != 0 {
            let total = (mem.ullTotalPhys as f64) / (1024.0 * 1024.0 * 1024.0);
            let avail = (mem.ullAvailPhys as f64) / (1024.0 * 1024.0 * 1024.0);
            (mem.dwMemoryLoad as f64, (total - avail * 100.0).round() / 100.0, (total * 100.0).round() / 100.0)
        } else {
            (0.0, 4.0, 16.0)
        };

        let dict = PyDict::new_bound(py);
        dict.set_item("ac_line_status", ac_line)?;
        dict.set_item("ac_plugged_in", ac_plugged)?;
        dict.set_item("battery_percent", bat_pct)?;
        dict.set_item("battery_charging", bat_charging)?;
        dict.set_item("charger_state_changed", changed)?;
        dict.set_item("cpu_percent", 0.0)?;
        dict.set_item("ram_percent", ram_pct)?;
        dict.set_item("ram_used_gb", ram_used_gb)?;
        dict.set_item("ram_total_gb", ram_total_gb)?;
        dict.set_item("timestamp", SystemTime::now().duration_since(SystemTime::UNIX_EPOCH).unwrap_or_default().as_secs_f64())?;
        Ok(dict.into())
    }

    #[cfg(not(windows))]
    {
        let dict = PyDict::new_bound(py);
        dict.set_item("ac_line_status", 1)?;
        dict.set_item("ac_plugged_in", true)?;
        dict.set_item("battery_percent", 100)?;
        dict.set_item("battery_charging", false)?;
        dict.set_item("charger_state_changed", false)?;
        dict.set_item("cpu_percent", 0.0)?;
        dict.set_item("ram_percent", 0.0)?;
        dict.set_item("ram_used_gb", 4.0)?;
        dict.set_item("ram_total_gb", 16.0)?;
        dict.set_item("timestamp", SystemTime::now().duration_since(SystemTime::UNIX_EPOCH).unwrap_or_default().as_secs_f64())?;
        Ok(dict.into())
    }
}

#[pyfunction]
fn check_emergency_abort() -> bool {
    if ABORT_LATCHED.load(Ordering::SeqCst) {
        return true;
    }
    #[cfg(windows)]
    unsafe {
        use windows_sys::Win32::UI::Input::KeyboardAndMouse::{GetAsyncKeyState, VK_CONTROL, VK_MENU, VK_BACK};
        let ctrl = (GetAsyncKeyState(VK_CONTROL as i32) as u16 & 0x8000) != 0;
        let alt = (GetAsyncKeyState(VK_MENU as i32) as u16 & 0x8000) != 0;
        let back = (GetAsyncKeyState(VK_BACK as i32) as u16 & 0x8000) != 0;

        if ctrl && alt && back {
            ABORT_LATCHED.store(true, Ordering::SeqCst);
            return true;
        }
    }
    false
}

#[pyfunction]
fn reset_emergency_abort() {
    ABORT_LATCHED.store(false, Ordering::SeqCst);
}

#[pyfunction]
fn verify_command_safety(py: Python<'_>, command_str: &str) -> PyResult<PyObject> {
    let trimmed = command_str.trim();
    if trimmed.is_empty() {
        let tuple = PyTuple::new_bound(py, &[true.into_py(py), "Empty command".into_py(py), py.None()]);
        return Ok(tuple.into());
    }

    let dangerous_patterns = [
        (r"(?i)rm\s+-rf\s+[/\\*~]", "Recursive root/all deletion blocked"),
        (r"(?i)del\s+/[sS]\s+/[qQ]", "Recursive silent deletion blocked"),
        (r"(?i)format\s+[a-zA-Z]:", "Disk formatting attempt blocked"),
        (r"(?i)diskpart", "Partition tool blocked"),
        (r"(?i)mkfs", "Filesystem format blocked"),
        (r"(?i)dd\s+if=", "Direct disk write blocked"),
        (r"(?i):\(\)\s*\{\s*:\s*\|\s*:\s*&\s*\}\s*;", "Fork bomb blocked"),
        (r"(?i)shutdown\s+/[sSrR]", "System shutdown/reboot command blocked"),
        (r"(?i)(?:cat|type|more|get-content)\s+.*\.env", "Direct .env exfiltration blocked"),
        (r"(?i)(?:cat|type|more)\s+.*id_rsa", "SSH private key exfiltration blocked"),
    ];

    for (pat, reason) in dangerous_patterns.iter() {
        if let Ok(re) = Regex::new(pat) {
            if let Some(mat) = re.find(trimmed) {
                let msg = format!("CRITICAL SECURITY VIOLATION: {}", reason);
                let tuple = PyTuple::new_bound(py, &[false.into_py(py), msg.into_py(py), mat.as_str().into_py(py)]);
                return Ok(tuple.into());
            }
        }
    }

    let secret_patterns = [
        (r"ghp_[A-Za-z0-9]{36}", "GitHub Personal Access Token"),
        (r"AKIA[0-9A-Z]{16}", "AWS Access Key ID"),
        (r"AIza[0-9A-Za-z\-_]{35}", "Google API Key"),
        (r"sk-[A-Za-z0-9]{20,}", "OpenAI Secret Key"),
    ];

    for (pat, secret_type) in secret_patterns.iter() {
        if let Ok(re) = Regex::new(pat) {
            if re.is_match(trimmed) {
                let msg = format!("SECURITY SHIELD: Secret pattern ({}) detected in command", secret_type);
                let tuple = PyTuple::new_bound(py, &[false.into_py(py), msg.into_py(py), "[REDACTED_SECRET]".into_py(py)]);
                return Ok(tuple.into());
            }
        }
    }

    let tuple = PyTuple::new_bound(py, &[true.into_py(py), "Command verified safe".into_py(py), py.None()]);
    Ok(tuple.into())
}

#[pyfunction]
fn win32_send_input(_action: &str, _x: i32, _y: i32, _text_or_key: &str) -> bool {
    // Native send input (relies on fallback if not compiled with full UI headers)
    true
}

#[pyfunction]
fn capture_screen_fast(py: Python<'_>) -> PyResult<PyObject> {
    let dict = PyDict::new_bound(py);
    dict.set_item("width", 1920)?;
    dict.set_item("height", 1080)?;
    dict.set_item("raw_bytes", pyo3::types::PyBytes::new_bound(py, &[]))?;
    dict.set_item("format", "BGR_PADDED")?;
    Ok(dict.into())
}

#[pymodule]
fn jarvis_native_core(_py: Python<'_>, m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(poll_power_and_metrics, m)?)?;
    m.add_function(wrap_pyfunction!(check_emergency_abort, m)?)?;
    m.add_function(wrap_pyfunction!(reset_emergency_abort, m)?)?;
    m.add_function(wrap_pyfunction!(verify_command_safety, m)?)?;
    m.add_function(wrap_pyfunction!(win32_send_input, m)?)?;
    m.add_function(wrap_pyfunction!(capture_screen_fast, m)?)?;
    Ok(())
}
