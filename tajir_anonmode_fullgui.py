#!/usr/bin/env python3
"""
Tajir Anonymous Mode - Full GUI (with AnonSurf)
Save as: /home/unknown/tajir_anonmode_fullgui.py
Run as root (recommended): sudo env DISPLAY=$DISPLAY XAUTHORITY=$XAUTHORITY python3 /home/unknown/tajir_anonmode_fullgui.py
"""

import tkinter as tk
from tkinter import messagebox, simpledialog, PhotoImage
import threading, subprocess, shutil, os, time, sys

# --------- Configuration ----------
INTERFACE = "eth0"
LOGO_PATH = "/home/unknown/logo.png"   # change to your logo path if available
ANONSURF_REPO = "https://github.com/Und3rf10w/kali-anonsurf.git"
ANONSURF_INSTALL_DIR = "/opt/kali-anonsurf"
APT_INSTALL_CMD = "apt-get update -y && apt-get install -y {}"
# Tools we consider "required"
REQUIRED_TOOLS = {
    "tor": "tor",
    "proxychains4": "proxychains4",
    "macchanger": "macchanger",
    "curl": "curl",
    "git": "git",
}
# ProtonVPN handled separately (package name 'protonvpn-cli')
# Anonsurf is handled separately (git repo installer)
# ----------------------------------

# --------- Helper utilities ----------
def append_status(text):
    """Thread-safe append to status_text"""
    def inner():
        status_text.config(state='normal')
        status_text.insert(tk.END, text + "\n")
        status_text.see(tk.END)
        status_text.config(state='disabled')
    root.after(0, inner)

def run_command(cmd, show_cmd=True, check=False):
    """Run shell command, return (rc, stdout+stderr)"""
    if show_cmd:
        append_status(f"$ {cmd}")
    try:
        completed = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        out = (completed.stdout or "") + (completed.stderr or "")
        if out.strip():
            append_status(out.strip())
        if check:
            completed.check_returncode()
        return completed.returncode, out
    except Exception as e:
        append_status(f"[Error] {e}")
        return 1, str(e)

def is_installed(binary):
    return shutil.which(binary) is not None

def ensure_root():
    if os.geteuid() != 0:
        messagebox.showwarning("Root required", "This tool should be run as root for installs and network changes.\n\nPlease re-run with sudo.")
        return False
    return True

# --------- Core functions ----------
def check_requirements_thread():
    append_status("Checking required tools...")
    missing = []
    for binname in REQUIRED_TOOLS:
        if not is_installed(binname):
            missing.append(binname)
            append_status(f"[Missing] {binname}")
        else:
            append_status(f"[OK] {binname} found")
    # check protonvpn-cli separately
    if not is_installed("protonvpn-cli"):
        append_status("[Info] protonvpn-cli not found (ProtonVPN features disabled until installed).")

    # check anonsurf
    if not is_installed("anonsurf"):
        append_status("[Info] anonsurf not found (Anonsurf features disabled until installed).")
    else:
        append_status("[OK] anonsurf found")

    if not missing:
        append_status("Core required tools are installed.")
        refresh_buttons_state()
        return

    # Ask user whether to install missing packages
    msg = "Missing tools detected:\n" + ", ".join(missing) + "\n\nInstall now? (requires root)"
    do_install = messagebox.askyesno("Install missing tools", msg)
    if not do_install:
        append_status("User declined installation. Some features may not work.")
        refresh_buttons_state()
        return

    append_status("Installing missing packages via apt (may take some time)...")
    apt_names = " ".join(REQUIRED_TOOLS[b] for b in missing)
    rc, out = run_command(APT_INSTALL_CMD.format(apt_names))
    if rc == 0:
        append_status("Installation finished. Re-checking tools...")
    else:
        append_status("[Error] Some installs failed; check logs above.")
    time.sleep(2)
    check_requirements_thread()

def check_requirements():
    threading.Thread(target=check_requirements_thread, daemon=True).start()

# MAC spoof
def spoof_mac_thread():
    append_status(f"Bringing {INTERFACE} down...")
    run_command(f"ip link set {INTERFACE} down")
    append_status("Running macchanger -r ...")
    if not is_installed("macchanger"):
        append_status("[Error] macchanger not installed.")
        return
    run_command(f"macchanger -r {INTERFACE}")
    run_command(f"ip link set {INTERFACE} up")
    rc, out = run_command(f"ip link show {INTERFACE} | grep ether", show_cmd=False)
    if rc == 0:
        append_status("MAC spoof complete.")
    else:
        append_status("[Error] Could not read new MAC.")
def spoof_mac():
    threading.Thread(target=spoof_mac_thread, daemon=True).start()

# Tor control
def start_tor_thread():
    append_status("Starting Tor service...")
    run_command("systemctl enable --now tor")
    time.sleep(1)
    run_command("systemctl status tor --no-pager", show_cmd=False)
def start_tor():
    threading.Thread(target=start_tor_thread, daemon=True).start()

def stop_tor_thread():
    append_status("Stopping Tor service...")
    run_command("systemctl stop tor")
    run_command("systemctl status tor --no-pager", show_cmd=False)
def stop_tor():
    threading.Thread(target=stop_tor_thread, daemon=True).start()

# Proxychains config
def configure_proxychains_thread():
    append_status("Configuring proxychains to use Tor...")
    conf_paths = ["/etc/proxychains4.conf", "/etc/proxychains.conf"]
    conf = None
    for p in conf_paths:
        if os.path.exists(p):
            conf = p
            break
    if not conf:
        append_status("[Error] proxychains config not found. Is proxychains4 installed?")
        return
    if not os.path.exists(conf + ".bak"):
        run_command(f"cp {conf} {conf}.bak")
    run_command(f"sed -i 's/^#dynamic_chain/dynamic_chain/' {conf}")
    run_command(f"sed -i 's/^strict_chain/#strict_chain/' {conf}")
    with open(conf, 'r') as f:
        contents = f.read()
    if "socks5 127.0.0.1 9050" not in contents:
        try:
            with open(conf, 'a') as f:
                f.write("\n# added by Tajir Anonymous Mode\nsocks5 127.0.0.1 9050\n")
            append_status("Added socks5 127.0.0.1 9050 to proxychains config.")
        except Exception as e:
            append_status(f"[Error] Unable to write proxychains config: {e}")
    append_status("Proxychains configured.")
def configure_proxychains():
    threading.Thread(target=configure_proxychains_thread, daemon=True).start()

# Test proxychains via ifconfig.me
def check_proxychains_via_curl_thread():
    append_status("Testing proxychains + Tor via ifconfig.me ...")
    if not is_installed("tor"):
        append_status("[Error] Tor not installed.")
        return
    if is_installed("proxychains4"):
        rc, out = run_command("proxychains4 curl -s ifconfig.me")
        if rc == 0:
            append_status(f"Proxychains ifconfig.me -> {out.strip()}")
        else:
            append_status("[Error] proxychains curl failed.")
    else:
        append_status("[Info] proxychains4 not installed.")
def check_proxychains_via_curl():
    threading.Thread(target=check_proxychains_via_curl_thread, daemon=True).start()

# ProtonVPN management
def install_protonvpn_thread():
    append_status("Installing ProtonVPN CLI (apt: protonvpn-cli)...")
    rc, out = run_command(APT_INSTALL_CMD.format("protonvpn-cli"))
    if rc == 0:
        append_status("ProtonVPN CLI installed.")
    else:
        append_status("[Error] ProtonVPN install failed.")
    refresh_buttons_state()
def install_protonvpn():
    threading.Thread(target=install_protonvpn_thread, daemon=True).start()

def protonvpn_login_thread():
    append_status("ProtonVPN CLI login (interactive)...")
    username = simpledialog.askstring("ProtonVPN Login", "ProtonVPN Username:")
    password = simpledialog.askstring("ProtonVPN Login", "ProtonVPN Password:", show='*')
    if not username or not password:
        append_status("ProtonVPN login cancelled.")
        return
    script = f"printf '%s\n%s\n' '{username}' '{password}' | protonvpn-cli login"
    rc, out = run_command(script)
    if rc == 0:
        append_status("ProtonVPN login completed.")
    else:
        append_status("[Warning] ProtonVPN login may have failed. Check logs above.")
def protonvpn_login():
    threading.Thread(target=protonvpn_login_thread, daemon=True).start()

def protonvpn_connect_thread():
    append_status("Connecting ProtonVPN (fastest free server)...")
    rc, out = run_command("protonvpn-cli c -f")
    if rc == 0:
        append_status("ProtonVPN connected.")
    else:
        append_status("[Error] ProtonVPN connect failed. Is protonvpn-cli installed and logged in?")
def protonvpn_connect():
    threading.Thread(target=protonvpn_connect_thread, daemon=True).start()

def protonvpn_disconnect_thread():
    append_status("Disconnecting ProtonVPN...")
    run_command("protonvpn-cli d")
    append_status("ProtonVPN disconnected.")
def protonvpn_disconnect():
    threading.Thread(target=protonvpn_disconnect_thread, daemon=True).start()

# AnonSurf install/start/stop
def is_anonsurf_installed():
    return is_installed("anonsurf") or os.path.exists("/usr/local/bin/anonsurf") or os.path.exists("/usr/bin/anonsurf")

def install_anonsurf_thread():
    append_status("Installing AnonSurf from repo...")
    # Ensure git present
    if not is_installed("git"):
        append_status("git not found — installing git...")
        run_command(APT_INSTALL_CMD.format("git"))
    # clone to /opt/kali-anonsurf
    if os.path.exists(ANONSURF_INSTALL_DIR):
        append_status(f"{ANONSURF_INSTALL_DIR} already exists. Pulling latest...")
        run_command(f"cd {ANONSURF_INSTALL_DIR} && git pull")
    else:
        run_command(f"git clone {ANONSURF_REPO} {ANONSURF_INSTALL_DIR}")
    # run installer
    installer = os.path.join(ANONSURF_INSTALL_DIR, "installer.sh")
    if os.path.exists(installer):
        run_command(f"chmod +x {installer} && {installer}")
        append_status("Ran AnonSurf installer script. If any apt key issues appear, check network and try again.")
    else:
        append_status("[Error] Installer script not found in cloned repo.")
    # refresh
    time.sleep(2)
    if is_anonsurf_installed():
        append_status("Anonsurf appears installed.")
    else:
        append_status("[Warning] Anonsurf not found after installation. See logs above.")
    refresh_buttons_state()

def install_anonsurf():
    threading.Thread(target=install_anonsurf_thread, daemon=True).start()

def anonsurf_start_thread():
    append_status("Starting AnonSurf (system-wide TOR via iptables)...")
    rc, out = run_command("anonsurf start")
    if rc == 0:
        append_status("AnonSurf started.")
    else:
        append_status("[Error] AnonSurf start reported an issue.")
def anonsurf_start():
    threading.Thread(target=anonsurf_start_thread, daemon=True).start()

def anonsurf_stop_thread():
    append_status("Stopping AnonSurf...")
    rc, out = run_command("anonsurf stop")
    if rc == 0:
        append_status("AnonSurf stopped.")
    else:
        append_status("[Error] AnonSurf stop reported an issue.")
def anonsurf_stop():
    threading.Thread(target=anonsurf_stop_thread, daemon=True).start()

# Clear histories
def clear_history_thread():
    append_status("Clearing bash/zsh histories (if present)...")
    paths = ["/root/.bash_history", "/root/.zsh_history", os.path.expanduser("~/.bash_history"), os.path.expanduser("~/.zsh_history")]
    for p in paths:
        if os.path.exists(p):
            run_command(f"shred -u {p}", show_cmd=False)
            append_status(f"Deleted {p}")
    append_status("History clear done.")
def clear_history():
    threading.Thread(target=clear_history_thread, daemon=True).start()

# Full Anonymous Mode
def start_full_anon_thread():
    append_status("Starting Full Anonymous Mode sequence...")
    spoof_mac_thread()
    time.sleep(1)
    start_tor_thread()
    time.sleep(1)
    configure_proxychains_thread()
    time.sleep(1)
    # prefer AnonSurf if installed (system-wide)
    if is_anonsurf_installed():
        append_status("Using AnonSurf (system-wide) for traffic tunneling.")
        anonsurf_start_thread()
    elif is_installed("protonvpn-cli"):
        append_status("Using ProtonVPN CLI for VPN.")
        protonvpn_connect_thread()
    else:
        append_status("[Info] No AnonSurf/ProtonVPN found; Tor+proxychains active but system traffic may leak.")
    append_status("Full Anonymous Mode sequence completed.")
def start_full_anon():
    threading.Thread(target=start_full_anon_thread, daemon=True).start()

def stop_all_thread():
    append_status("Stopping anonymity services...")
    if is_anonsurf_installed():
        run_command("anonsurf stop", show_cmd=False)
    if is_installed("protonvpn-cli"):
        run_command("protonvpn-cli d", show_cmd=False)
    run_command("systemctl stop tor", show_cmd=False)
    append_status("Stopped Tor/AnonSurf/ProtonVPN (if running).")
def stop_all():
    threading.Thread(target=stop_all_thread, daemon=True).start()

# ---------- GUI ----------
root = tk.Tk()
root.title("Tajir Anonymous Mode")
root.geometry("760x720")
root.config(bg="black")

# show logo or title
if os.path.exists(LOGO_PATH):
    try:
        logo_img = PhotoImage(file=LOGO_PATH)
        lbl_logo = tk.Label(root, image=logo_img, bg="black")
        lbl_logo.pack(pady=8)
    except Exception:
        tk.Label(root, text="Tajir Anonymous Mode", fg="lime", bg="black", font=("Consolas", 24, "bold")).pack(pady=10)
else:
    tk.Label(root, text="Tajir Anonymous Mode", fg="lime", bg="black", font=("Consolas", 24, "bold")).pack(pady=12)

# Buttons
frame = tk.Frame(root, bg="black")
frame.pack(pady=4)

btn_specs = [
    ("Check & Install Tools", check_requirements),
    ("Spoof MAC Address", spoof_mac),
    ("Start Tor Service", start_tor),
    ("Stop Tor Service", stop_tor),
    ("Configure ProxyChains", configure_proxychains),
    ("Test Proxychains (ifconfig.me)", check_proxychains_via_curl),
    ("Install AnonSurf (git)", install_anonsurf),
    ("Start AnonSurf", anonsurf_start),
    ("Stop AnonSurf", anonsurf_stop),
    ("Install ProtonVPN CLI", install_protonvpn),
    ("ProtonVPN Login", protonvpn_login),
    ("Connect ProtonVPN (fast)", protonvpn_connect),
    ("Disconnect ProtonVPN", protonvpn_disconnect),
    ("Clear Bash History", clear_history),
    ("Start Full Anonymous Mode", start_full_anon),
    ("Stop All (Tor+VPN+AnonSurf)", stop_all),
]
buttons = []
for (txt, cmd) in btn_specs:
    b = tk.Button(frame, text=txt, width=46, bg="green", fg="black",
                  font=("Consolas", 11, "bold"),
                  command=lambda c=cmd: threading.Thread(target=c, daemon=True).start())
    b.pack(pady=3)
    buttons.append(b)

# Status box
status_text = tk.Text(root, height=22, bg="black", fg="lime", font=("Consolas", 10))
status_text.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)
status_text.config(state='disabled')

hint = tk.Label(root, text="Run as root. Installs use apt and may take time. If AnonSurf install errors appear (repo keys), retry later or check network.", bg="black", fg="white")
hint.pack(pady=4)

# Refresh button states depending on installed tools
def refresh_buttons_state():
    # enable all by default
    for b in buttons:
        b.config(state='normal')
    # protonvpn actions disabled if not installed
    if not is_installed("protonvpn-cli"):
        for b in buttons:
            if b.cget("text") in ("ProtonVPN Login", "Connect ProtonVPN", "Disconnect ProtonVPN"):
                b.config(state='disabled')
    # disable anonsurf start/stop if anonsurf not installed
    if not is_anonsurf_installed():
        for b in buttons:
            if b.cget("text") in ("Start AnonSurf", "Stop AnonSurf"):
                b.config(state='disabled')
    root.update_idletasks()

# initial check
root.after(200, lambda: threading.Thread(target=check_requirements_thread, daemon=True).start())
root.after(500, refresh_buttons_state)

# warn if not root
if os.geteuid() != 0:
    append_status("[Warning] Not running as root. Please run with sudo to allow installs and network changes.")

root.mainloop()
