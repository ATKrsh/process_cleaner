import psutil
import win32api
import datetime
import time
import subprocess
import os
import winreg
import win32gui
import win32process

if os.name == 'nt':
    _original_popen = subprocess.Popen
    def _patched_popen(*args, **kwargs):
        if 'creationflags' not in kwargs:
            kwargs['creationflags'] = 0x08000000 # CREATE_NO_WINDOW
        return _original_popen(*args, **kwargs)
    subprocess.Popen = _patched_popen

from constants import SYSTEM_WHITELIST, KNOWN_BLOATWARE, LAYMAN_DESCRIPTIONS

# Cache for I/O speed calculation
_io_cache = {}
# Try importing GPUtil for GPU monitoring
try:
    import GPUtil
    HAS_GPUTIL = True
except ImportError:
    HAS_GPUTIL = False

def get_file_description(filepath):
    try:
        lang, codepage = win32api.GetFileVersionInfo(filepath, '\\VarFileInfo\\Translation')[0]
        str_info = u'\\StringFileInfo\\%04X%04X\\%s' % (lang, codepage, "FileDescription")
        desc = win32api.GetFileVersionInfo(filepath, str_info)
        return desc if desc else "No description available."
    except Exception:
        return ""

def get_all_processes():
    """
    Returns a list of dictionaries containing hierarchical process information.
    """
    global _io_cache
    process_dict = {}
    current_time = time.time()
    
    fg_pid = -1
    try:
        hwnd = win32gui.GetForegroundWindow()
        if hwnd:
            _, fg_pid = win32process.GetWindowThreadProcessId(hwnd)
    except:
        pass
        
    user_dir = os.path.expanduser("~").lower()
    
    # Pre-fetch startup entries to avoid hitting the registry per process
    startup_entries = []
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_READ)
        for i in range(winreg.QueryInfoKey(key)[1]):
            s_name, s_value, _ = winreg.EnumValue(key, i)
            # value usually contains quotes if it has spaces
            startup_entries.append(s_value.lower().replace('"', ''))
        winreg.CloseKey(key)
    except Exception:
        pass
    
    # First pass: collect all processes
    for proc in psutil.process_iter(['pid', 'name', 'memory_info', 'ppid', 'exe', 'create_time', 'cpu_percent'], ad_value=None):
        try:
            info = proc.info
            name = info.get('name', 'Unknown')
            if not name:
                name = 'Unknown'
            
            mem = 0.0
            if info.get('memory_info'):
                mem = info['memory_info'].rss / (1024 * 1024)
                
            pid = info.get('pid', -1)
            ppid = info.get('ppid', -1)
            exe = info.get('exe') or "Unknown Location"
            
            create_time = info.get('create_time', 0)
            duration = "Unknown"
            if create_time:
                delta = datetime.datetime.now() - datetime.datetime.fromtimestamp(create_time)
                duration = str(datetime.timedelta(seconds=int(delta.total_seconds())))

            cpu = 0.0
            try:
                cpu = proc.cpu_percent(interval=None) 
            except:
                pass

            if pid <= 0:
                continue

            # I/O Speed Calculation
            io_speed_mbs = 0.0
            try:
                counters = proc.io_counters()
                # Windows io_counters has read_bytes and write_bytes (combines disk + net)
                total_bytes = counters.read_bytes + counters.write_bytes
                if pid in _io_cache:
                    last_bytes, last_time = _io_cache[pid]
                    delta_bytes = total_bytes - last_bytes
                    delta_t = current_time - last_time
                    if delta_t > 0:
                        io_speed_mbs = (delta_bytes / delta_t) / (1024 * 1024)
                _io_cache[pid] = (total_bytes, current_time)
            except (psutil.AccessDenied, AttributeError):
                pass
                
            # Internet Connectivity
            is_connected = False
            try:
                conns = proc.connections(kind='inet')
                for c in conns:
                    if c.status == 'ESTABLISHED' and c.raddr:
                        if c.raddr.ip not in ['127.0.0.1', '0.0.0.0', '::1']:
                            is_connected = True
                            break
            except psutil.AccessDenied:
                pass

            desc = LAYMAN_DESCRIPTIONS.get(name.lower(), "")
            if not desc and exe != "Unknown Location":
                desc = get_file_description(exe)
            if not desc:
                desc = "A background process."
                
            is_startup = False
            if exe != "Unknown Location":
                for s_entry in startup_entries:
                    if exe.lower() in s_entry:
                        is_startup = True
                        break

            process_dict[pid] = {
                'pid': pid,
                'ppid': ppid,
                'name': name,
                'memory_mb': round(mem, 1),
                'cpu_percent': round(cpu, 1),
                'io_speed': round(io_speed_mbs, 2),
                'internet': "Yes" if is_connected else "No",
                'is_system': is_system_process(name),
                'is_bloatware': is_unnecessary(name),
                'is_heavy': cpu > 20.0 or mem > 500.0,
                'is_in_focus': pid == fg_pid,
                'is_user_added': exe != "Unknown Location" and user_dir in exe.lower(),
                'exe': exe,
                'duration': duration,
                'description': desc,
                'startup': is_startup,
                'selected': False,
                'children': []
            }
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
            
    # Cleanup old IO cache entries
    current_pids = set(process_dict.keys())
    _io_cache = {pid: v for pid, v in _io_cache.items() if pid in current_pids}

    # Second pass: build hierarchy
    hierarchical_processes = []
    
    for pid, proc_data in process_dict.items():
        ppid = proc_data['ppid']
        if ppid in process_dict:
            process_dict[ppid]['children'].append(proc_data)
        
    for pid, proc_data in process_dict.items():
        if proc_data['ppid'] not in process_dict:
            hierarchical_processes.append(proc_data)
            
    hierarchical_processes.sort(key=lambda x: x['memory_mb'], reverse=True)
    return hierarchical_processes

def detect_system_lag():
    """
    Returns (is_lagging, culprit_pids)
    Checks if overall CPU, Memory, HDD, or GPU is high.
    """
    cpu_percent = psutil.cpu_percent(interval=1)
    mem_percent = psutil.virtual_memory().percent
    
    # Basic HDD Lag check: Disk I/O busy check is hard without admin in Windows, so we check total IO
    # If the system is writing/reading more than ~100MB/s total, it might be heavily loaded
    disk_busy = False
    try:
        io_1 = psutil.disk_io_counters()
        time.sleep(0.5)
        io_2 = psutil.disk_io_counters()
        delta_mb = ((io_2.read_bytes - io_1.read_bytes) + (io_2.write_bytes - io_1.write_bytes)) / (1024 * 1024)
        if delta_mb > 50: # More than 100MB/s roughly
            disk_busy = True
    except:
        pass
        
    gpu_busy = False
    if HAS_GPUTIL:
        try:
            gpus = GPUtil.getGPUs()
            if any(g.load > 0.90 for g in gpus):
                gpu_busy = True
        except:
            pass

    lagging = False
    culprits = []
    
    if cpu_percent > 90 or mem_percent > 90 or disk_busy or gpu_busy:
        lagging = True
        procs = []
        for p in psutil.process_iter(['pid', 'cpu_percent', 'memory_percent']):
            try:
                # Add basic CPU/Mem metrics to find culprit
                procs.append((p.info['pid'], p.info['cpu_percent'] or 0, p.info['memory_percent'] or 0))
            except:
                pass
        
        # Sort by CPU usually as the main generic indicator
        procs.sort(key=lambda x: x[1], reverse=True)
        culprits = [p[0] for p in procs[:3]]
        
    return lagging, culprits

def is_system_process(name):
    return name.lower() in SYSTEM_WHITELIST

def is_unnecessary(name):
    return name.lower() in KNOWN_BLOATWARE

def kill_process(pid):
    try:
        proc = psutil.Process(pid)
        name = proc.name()
        if is_system_process(name):
            print(f"Refusing to kill system process: {name}")
            return False
            
        proc.terminate()
        proc.wait(timeout=3)
        return True
    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.TimeoutExpired) as e:
        print(f"Failed to kill PID {pid}: {e}")
        return False

def kill_processes(pids):
    count = 0
    for pid in pids:
        if kill_process(pid):
            count += 1
    return count

def force_kill_process(pid):
    try:
        proc = psutil.Process(pid)
        name = proc.name()
        if is_system_process(name):
            print(f"Refusing to kill system process: {name}")
            return False
        proc.kill()
        proc.wait(timeout=3)
        return True
    except Exception as e:
        print(f"Failed to force kill PID {pid}: {e}")
        return False

def suspend_process(pid):
    try:
        psutil.Process(pid).suspend()
        return True
    except Exception as e:
        print(f"Failed to suspend PID {pid}: {e}")
        return False

def resume_process(pid):
    try:
        psutil.Process(pid).resume()
        return True
    except Exception as e:
        print(f"Failed to resume PID {pid}: {e}")
        return False

def set_process_priority(pid, priority_class):
    try:
        psutil.Process(pid).nice(priority_class)
        return True
    except Exception as e:
        print(f"Failed to set priority for PID {pid}: {e}")
        return False

def open_file_location(filepath):
    if filepath and filepath != "Unknown Location":
        subprocess.Popen(f'explorer /select,"{filepath}"')

def add_startup_entry(name, filepath):
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_SET_VALUE)
        winreg.SetValueEx(key, name, 0, winreg.REG_SZ, f'"{filepath}"')
        winreg.CloseKey(key)
        return True
    except Exception as e:
        print(f"Failed to add startup entry: {e}")
        return False

def remove_startup_entry(name):
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_SET_VALUE)
        winreg.DeleteValue(key, name)
        winreg.CloseKey(key)
        return True
    except Exception as e:
        print(f"Failed to remove startup entry: {e}")
        return False

