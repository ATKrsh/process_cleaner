import tkinter as tk
from tkinter import ttk
import customtkinter as ctk
import threading
import time
from tkinter import messagebox
from process_manager import (get_all_processes, kill_processes, detect_system_lag, is_system_process,
                             suspend_process, resume_process, force_kill_process, set_process_priority,
                             open_file_location, add_startup_entry, remove_startup_entry)
import psutil

class ToolTip(object):
    def __init__(self, widget):
        self.widget = widget
        self.tipwindow = None
        self.text = ""

    def showtip(self, text, x, y):
        self.text = text
        if self.tipwindow or not self.text:
            return
        self.tipwindow = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(1)
        tw.wm_geometry(f"+{x+15}+{y+15}")
        label = tk.Label(tw, text=self.text, justify=tk.LEFT,
                         background="#2b2b2b", foreground="white", relief=tk.SOLID, borderwidth=1,
                         font=("Arial", "10", "normal"), padx=5, pady=5)
        label.pack(ipadx=1)

    def hidetip(self):
        tw = self.tipwindow
        self.tipwindow = None
        if tw:
            tw.destroy()

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Windows Process Cleaner (Advanced)")
        self.geometry("1300x700")
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        
        # Top Frame for controls
        self.top_frame = ctk.CTkFrame(self)
        self.top_frame.grid(row=0, column=0, padx=10, pady=(10,0), sticky="ew")
        
        self.reload_btn = ctk.CTkButton(self.top_frame, text="Reload List", command=self.refresh_list_threaded)
        self.reload_btn.pack(side="left", padx=10, pady=10)
        
        self.refresh_btn = ctk.CTkButton(self.top_frame, text="Refresh (Kill Bloatware)", command=self.clean_bloatware_threaded, fg_color="#d35400", hover_color="#e67e22")
        self.refresh_btn.pack(side="left", padx=10, pady=10)

        self.end_sel_btn = ctk.CTkButton(self.top_frame, text="End Selected", command=self.end_selected_threaded, fg_color="#8e44ad", hover_color="#9b59b6")
        self.end_sel_btn.pack(side="left", padx=5, pady=10)

        self.expand_btn = ctk.CTkButton(self.top_frame, text="Expand All", command=self.expand_all, width=80)
        self.expand_btn.pack(side="left", padx=5, pady=10)
        
        self.collapse_btn = ctk.CTkButton(self.top_frame, text="Collapse All", command=self.collapse_all, width=80)
        self.collapse_btn.pack(side="left", padx=5, pady=10)

        self.reset_btn = ctk.CTkButton(self.top_frame, text="Reset (Fresh Install State)", command=self.reset_system_threaded, fg_color="#c0392b", hover_color="#e74c3c")
        self.reset_btn.pack(side="right", padx=10, pady=10)

        self.reset_ui_btn = ctk.CTkButton(self.top_frame, text="⟲ Reset UI", command=self.reset_ui_settings, width=80, fg_color="#34495e", hover_color="#2c3e50")
        self.reset_ui_btn.pack(side="right", padx=5, pady=10)

        self.font_slider = ctk.CTkSlider(self.top_frame, from_=8, to=24, number_of_steps=16, command=self.change_font_size, width=100)
        self.font_slider.set(10)
        self.font_slider.pack(side="right", padx=5, pady=10)
        
        self.font_label = ctk.CTkLabel(self.top_frame, text="Font:")
        self.font_label.pack(side="right", padx=(5, 0), pady=10)

        self.spacing_slider = ctk.CTkSlider(self.top_frame, from_=50, to=200, number_of_steps=30, command=self.change_column_spacing, width=100)
        self.spacing_slider.set(100)
        self.spacing_slider.pack(side="right", padx=5, pady=10)
        
        self.spacing_label = ctk.CTkLabel(self.top_frame, text="Spacing (%):")
        self.spacing_label.pack(side="right", padx=(10, 0), pady=10)
        
        # Treeview Frame
        self.tree_frame = ctk.CTkFrame(self)
        self.tree_frame.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
        self.tree_frame.grid_columnconfigure(0, weight=1)
        self.tree_frame.grid_rowconfigure(0, weight=1)

        style = ttk.Style()
        style.theme_use("default")
        style.configure("Treeview", background="#2a2d2e", foreground="white", rowheight=25, fieldbackground="#2a2d2e", font=("Arial", 10))
        style.configure("Treeview.Heading", font=("Arial", 10, "bold"))
        style.map('Treeview', background=[('selected', '#22559b')])

        self.tree = ttk.Treeview(self.tree_frame, columns=("Select", "PID", "Memory", "CPU", "Uptime", "IO", "Internet", "Status", "Startup", "Location"), show="tree headings")
        self.tree.heading("#0", text="Process Name", anchor="w", command=lambda c="#0": self.treeview_sort_column(self.tree, c, False))
        self.tree.heading("Select", text="Sel", anchor="w", command=lambda c="Select": self.treeview_sort_column(self.tree, c, False))
        self.tree.heading("PID", text="PID", anchor="w", command=lambda c="PID": self.treeview_sort_column(self.tree, c, False))
        self.tree.heading("Memory", text="Memory (MB)", anchor="w", command=lambda c="Memory": self.treeview_sort_column(self.tree, c, False))
        self.tree.heading("CPU", text="CPU %", anchor="w", command=lambda c="CPU": self.treeview_sort_column(self.tree, c, False))
        self.tree.heading("Uptime", text="Uptime", anchor="w", command=lambda c="Uptime": self.treeview_sort_column(self.tree, c, False))
        self.tree.heading("IO", text="I/O (MB/s)", anchor="w", command=lambda c="IO": self.treeview_sort_column(self.tree, c, False))
        self.tree.heading("Internet", text="Internet", anchor="w", command=lambda c="Internet": self.treeview_sort_column(self.tree, c, False))
        self.tree.heading("Status", text="Status", anchor="w", command=lambda c="Status": self.treeview_sort_column(self.tree, c, False))
        self.tree.heading("Startup", text="Startup", anchor="w", command=lambda c="Startup": self.treeview_sort_column(self.tree, c, False))
        self.tree.heading("Location", text="Location", anchor="w", command=lambda c="Location": self.treeview_sort_column(self.tree, c, False))
        
        self.base_widths = {
            "#0": 250, "Select": 40, "PID": 60, "Memory": 80, "CPU": 60, 
            "Uptime": 80, "IO": 80, "Internet": 60, "Status": 100, 
            "Startup": 60, "Location": 250
        }
        
        for col, bw in self.base_widths.items():
            self.tree.column(col, width=bw)

        self.tree.grid(row=0, column=0, sticky="nsew")
        
        scrollbar = ttk.Scrollbar(self.tree_frame, orient="vertical", command=self.tree.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        # Status Label
        self.status_label = ctk.CTkLabel(self, text="Ready", anchor="w")
        self.status_label.grid(row=2, column=0, padx=10, pady=(0, 10), sticky="ew")

        # Warning Label for lag
        self.lag_label = ctk.CTkLabel(self, text="", text_color="red", anchor="e")
        self.lag_label.grid(row=2, column=0, padx=10, pady=(0, 10), sticky="e")

        self.process_map = {}
        self.tooltip = ToolTip(self.tree)
        self.last_hovered = None

        self.tree.bind("<Motion>", self.on_tree_motion)
        self.tree.bind("<Leave>", lambda e: self.tooltip.hidetip())
        self.tree.bind("<Button-1>", self.on_tree_click)
        self.tree.bind("<ButtonPress-1>", self.on_tree_button_press, add='+')
        self.tree.bind("<ButtonRelease-1>", self.on_tree_button_release, add='+')
        self.tree.bind("<Button-3>", self.on_tree_right_click)
        
        self._drag_data = {'col': None, 'x': 0}

        self.create_context_menu()

        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self.lag_monitor_loop, daemon=True)
        self.monitor_thread.start()

        self.refresh_list_threaded()

    def create_context_menu(self):
        self.context_menu = tk.Menu(self, tearoff=0, bg="#2b2b2b", fg="white")
        self.context_menu.add_command(label="End Task", command=self.cmd_end_task)
        self.context_menu.add_command(label="Force End", command=self.cmd_force_end)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Freeze (Suspend)", command=self.cmd_freeze)
        self.context_menu.add_command(label="Resume", command=self.cmd_resume)
        self.context_menu.add_separator()
        
        self.priority_menu = tk.Menu(self.context_menu, tearoff=0, bg="#2b2b2b", fg="white")
        self.priority_menu.add_command(label="Realtime", command=lambda: self.cmd_set_priority(psutil.REALTIME_PRIORITY_CLASS))
        self.priority_menu.add_command(label="High", command=lambda: self.cmd_set_priority(psutil.HIGH_PRIORITY_CLASS))
        self.priority_menu.add_command(label="Above Normal", command=lambda: self.cmd_set_priority(psutil.ABOVE_NORMAL_PRIORITY_CLASS))
        self.priority_menu.add_command(label="Normal", command=lambda: self.cmd_set_priority(psutil.NORMAL_PRIORITY_CLASS))
        self.priority_menu.add_command(label="Below Normal", command=lambda: self.cmd_set_priority(psutil.BELOW_NORMAL_PRIORITY_CLASS))
        self.priority_menu.add_command(label="Low", command=lambda: self.cmd_set_priority(psutil.IDLE_PRIORITY_CLASS))
        self.context_menu.add_cascade(label="Set Priority", menu=self.priority_menu)
        
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Go to Location", command=self.cmd_location)
        self.context_target = None

    def on_tree_right_click(self, event):
        item = self.tree.identify_row(event.y)
        if item:
            self.tree.selection_set(item)
            self.context_target = item
            self.context_menu.post(event.x_root, event.y_root)

    def cmd_end_task(self):
        if self.context_target and self.context_target in self.process_map:
            pid = self.process_map[self.context_target]['pid']
            kill_processes([pid])
            self.refresh_list_threaded()
            
    def cmd_force_end(self):
        if self.context_target and self.context_target in self.process_map:
            pid = self.process_map[self.context_target]['pid']
            force_kill_process(pid)
            self.refresh_list_threaded()

    def cmd_freeze(self):
        if self.context_target and self.context_target in self.process_map:
            pid = self.process_map[self.context_target]['pid']
            suspend_process(pid)

    def cmd_resume(self):
        if self.context_target and self.context_target in self.process_map:
            pid = self.process_map[self.context_target]['pid']
            resume_process(pid)
            
    def cmd_set_priority(self, p_class):
        if self.context_target and self.context_target in self.process_map:
            pid = self.process_map[self.context_target]['pid']
            set_process_priority(pid, p_class)

    def cmd_location(self):
        if self.context_target and self.context_target in self.process_map:
            exe = self.process_map[self.context_target]['exe']
            open_file_location(exe)

    def on_tree_click(self, event):
        region = self.tree.identify("region", event.x, event.y)
        if region == "cell":
            column = self.tree.identify_column(event.x)
            item = self.tree.identify_row(event.y)
            if item:
                col_idx = int(column[1:]) - 1  # #1 is column 0 ("Select")
                if col_idx == 0:  # Select column
                    proc = self.process_map[item]
                    proc['selected'] = not proc.get('selected', False)
                    new_val = "☑" if proc['selected'] else "☐"
                    self.tree.set(item, "Select", new_val)
                elif col_idx == 8: # Startup column
                    proc = self.process_map[item]
                    proc['startup'] = not proc.get('startup', False)
                    new_val = "☑" if proc['startup'] else "☐"
                    self.tree.set(item, "Startup", new_val)
                    if proc['startup']:
                        add_startup_entry(proc['name'], proc['exe'])
                    else:
                        remove_startup_entry(proc['name'])

    def expand_all(self):
        def _expand(item):
            self.tree.item(item, open=True)
            for child in self.tree.get_children(item):
                _expand(child)
        for item in self.tree.get_children(''):
            _expand(item)

    def collapse_all(self):
        def _collapse(item):
            self.tree.item(item, open=False)
            for child in self.tree.get_children(item):
                _collapse(child)
        for item in self.tree.get_children(''):
            _collapse(item)

    def reset_ui_settings(self):
        # Reset Font
        self.font_slider.set(10)
        self.change_font_size(10)
        
        # Reset Spacing
        self.spacing_slider.set(100)
        self.change_column_spacing(100)
        
        # Reset Column Order
        default_cols = ("Select", "PID", "Memory", "CPU", "Uptime", "IO", "Internet", "Status", "Startup", "Location")
        self.tree.configure(displaycolumns=default_cols)

    def change_font_size(self, value):
        size = int(value)
        style = ttk.Style()
        style.configure("Treeview", font=("Arial", size), rowheight=size + 15)
        style.configure("Treeview.Heading", font=("Arial", size, "bold"))

    def change_column_spacing(self, value):
        scale = float(value) / 100.0
        for col, bw in self.base_widths.items():
            self.tree.column(col, width=int(bw * scale))

    def on_tree_button_press(self, event):
        region = self.tree.identify("region", event.x, event.y)
        if region == "heading":
            col = self.tree.identify_column(event.x)
            self._drag_data['col'] = col
            self._drag_data['x'] = event.x

    def on_tree_button_release(self, event):
        if self._drag_data.get('col') is None:
            return
            
        region = self.tree.identify("region", event.x, event.y)
        if region == "heading":
            end_col = self.tree.identify_column(event.x)
            start_col = self._drag_data['col']
            
            # Drag to rearrange column
            if start_col != end_col and abs(event.x - self._drag_data['x']) > 10:
                if start_col != '#0' and end_col != '#0':
                    current_cols = list(self.tree.cget("displaycolumns"))
                    if not current_cols or current_cols[0] == '#all':
                        current_cols = list(self.tree.cget("columns"))
                        
                    start_idx = int(start_col[1:]) - 1
                    end_idx = int(end_col[1:]) - 1
                    
                    if start_idx < len(current_cols) and end_idx < len(current_cols):
                        actual_start_col = current_cols[start_idx]
                        current_cols.pop(start_idx)
                        current_cols.insert(end_idx, actual_start_col)
                        self.tree.configure(displaycolumns=current_cols)
                        
        self._drag_data = {'col': None, 'x': 0}

    def get_sort_key(self, col):
        if col in ('PID', 'Memory', 'CPU', 'IO'):
            def key_func(t):
                try:
                    return float(str(t[0]).replace(' MB/s', '').replace(' MB', '').replace('%', '').replace(' N/A', '-1').strip())
                except ValueError:
                    return 0.0
            return key_func
        elif col == 'Uptime':
            def key_func(t):
                val = str(t[0])
                if val == 'Unknown' or not val:
                    return -1.0
                try:
                    days = 0
                    if 'day' in val:
                        parts = val.split(' day')
                        days = int(parts[0])
                        val = parts[1].split(', ')[-1] # get the HH:MM:SS part
                    
                    parts = val.split(':')
                    if len(parts) == 3:
                        return days*86400 + float(parts[0])*3600 + float(parts[1])*60 + float(parts[2])
                    return 0.0
                except:
                    return 0.0
            return key_func
        else:
            return lambda t: str(t[0]).lower()

    def treeview_sort_column(self, tv, col, reverse):
        if col == '#0':
            l = [(tv.item(k, 'text'), k) for k in tv.get_children('')]
        else:
            l = [(tv.set(k, col), k) for k in tv.get_children('')]
            
        l.sort(key=self.get_sort_key(col), reverse=reverse)
            
        for index, (val, k) in enumerate(l):
            tv.move(k, '', index)
            self._sort_children(tv, k, col, reverse)
            
        tv.heading(col, command=lambda _col=col: self.treeview_sort_column(tv, _col, not reverse))
        
    def _sort_children(self, tv, item, col, reverse):
        children = tv.get_children(item)
        if not children: return
        
        if col == '#0':
            l = [(tv.item(k, 'text'), k) for k in children]
        else:
            l = [(tv.set(k, col), k) for k in children]
            
        l.sort(key=self.get_sort_key(col), reverse=reverse)
            
        for index, (val, k) in enumerate(l):
            tv.move(k, item, index)
            self._sort_children(tv, k, col, reverse)

    def on_tree_motion(self, event):
        item_id = self.tree.identify_row(event.y)
        if item_id:
            if item_id != self.last_hovered:
                self.last_hovered = item_id
                self.tooltip.hidetip()
                proc_data = self.process_map.get(item_id)
                if proc_data:
                    tip_text = f"Description: {proc_data['description']}\n"
                    tip_text += f"Location: {proc_data['exe']}"
                    x = self.tree.winfo_pointerx()
                    y = self.tree.winfo_pointery()
                    self.tooltip.showtip(tip_text, x, y)
        else:
            self.last_hovered = None
            self.tooltip.hidetip()

    def lag_monitor_loop(self):
        while self.monitoring:
            is_lagging, culprits = detect_system_lag()
            if is_lagging:
                self.after(0, self.update_lag_warning, culprits)
            else:
                self.after(0, self.clear_lag_warning)
            time.sleep(2)

    def update_lag_warning(self, culprits):
        if culprits:
            names = []
            for item in self.tree.get_children(''):
                self._find_names_for_pids(item, culprits, names)
            self.lag_label.configure(text=f"System Lag Detected! Top consumers: {', '.join(names)}")
        else:
            self.lag_label.configure(text="System Lag Detected!")

    def _find_names_for_pids(self, item, pids, names_list):
        proc_data = self.process_map.get(item)
        if proc_data and proc_data['pid'] in pids:
            if proc_data['name'] not in names_list:
                names_list.append(proc_data['name'])
        for child in self.tree.get_children(item):
            self._find_names_for_pids(child, pids, names_list)

    def clear_lag_warning(self):
        self.lag_label.configure(text="")

    def refresh_list_threaded(self):
        self.status_label.configure(text="Scanning processes...")
        self.reload_btn.configure(state="disabled")
        threading.Thread(target=self.refresh_list, daemon=True).start()

    def refresh_list(self):
        processes = get_all_processes()
        self.after(0, self.update_gui_list, processes)

    def insert_process(self, parent_iid, proc):
        status = ""
        tags = ()
        # Priority order for tags based on user request
        if proc.get('is_in_focus'):
            status = "IN FOCUS"
            tags = ("in_focus",)
        elif proc.get('is_heavy'):
            status = "HEAVY LOAD"
            tags = ("heavy_load",)
        elif proc.get('is_bloatware'):
            status = "BLOATWARE"
            tags = ("bloatware",)
        elif proc.get('startup'):
            status = "STARTUP"
            tags = ("startup_proc",)
        elif proc.get('is_user_added'):
            status = "USER ADDED"
            tags = ("user_added",)
        elif proc.get('is_system'):
            status = "SYSTEM"
            tags = ("system",)

        sel_text = "☑" if proc.get('selected') else "☐"
        start_text = "☑" if proc.get('startup') else "☐"

        iid = self.tree.insert(parent_iid, "end", text=proc['name'], 
                               values=(sel_text, proc['pid'], proc['memory_mb'], proc['cpu_percent'], 
                                       proc['duration'], proc['io_speed'], proc['internet'], status, start_text, proc['exe']),
                               tags=tags, open=True)
        self.process_map[iid] = proc
        
        for child in proc['children']:
            self.insert_process(iid, child)

    def update_gui_list(self, processes):
        self.tree.delete(*self.tree.get_children())
        self.process_map.clear()
        
        for proc in processes:
            self.insert_process("", proc)

        self.tree.tag_configure("in_focus", foreground="green")
        self.tree.tag_configure("heavy_load", foreground="red")
        self.tree.tag_configure("bloatware", foreground="purple")
        self.tree.tag_configure("startup_proc", foreground="yellow")
        self.tree.tag_configure("user_added", foreground="cyan")
        self.tree.tag_configure("system", foreground="gray")

        self.status_label.configure(text=f"Loaded process tree.")
        self.reload_btn.configure(state="normal")

    def clean_bloatware_threaded(self):
        # Auto clean processes marked as bloatware
        pids_to_kill = []
        for iid, data in self.process_map.items():
            if data['is_bloatware']:
                pids_to_kill.append(data['pid'])
        
        if not pids_to_kill:
            self.status_label.configure(text="No bloatware found to clean.")
            return

        self.status_label.configure(text=f"Cleaning {len(pids_to_kill)} bloatware processes...")
        self.refresh_btn.configure(state="disabled")
        threading.Thread(target=self.clean_selected, args=(pids_to_kill,), daemon=True).start()

    def end_selected_threaded(self):
        pids_to_kill = []
        for iid, data in self.process_map.items():
            if data.get('selected'):
                pids_to_kill.append(data['pid'])
        
        if not pids_to_kill:
            self.status_label.configure(text="No processes selected to end.")
            return

        self.status_label.configure(text=f"Ending {len(pids_to_kill)} selected processes...")
        self.end_sel_btn.configure(state="disabled")
        threading.Thread(target=self.clean_selected, args=(pids_to_kill,), daemon=True).start()

    def reset_system_threaded(self):
        if not messagebox.askyesno("Confirm Reset", "Are you sure? This will force close ALL processes not found in a fresh Windows installation. This may close your browser and unsaved work!"):
            return

        pids_to_kill = []
        for iid, data in self.process_map.items():
            # Don't kill our app, system processes, or python environment running the app
            if not is_system_process(data['name']):
                pids_to_kill.append(data['pid'])
                
        if not pids_to_kill:
            self.status_label.configure(text="System is already clean.")
            return
            
        self.status_label.configure(text=f"Resetting system, attempting to kill {len(pids_to_kill)} non-essential processes...")
        self.reset_btn.configure(state="disabled")
        threading.Thread(target=self.clean_selected, args=(pids_to_kill,), daemon=True).start()

    def clean_selected(self, pids_to_kill):
        killed_count = kill_processes(pids_to_kill)
        self.after(0, self.on_clean_finished, killed_count, len(pids_to_kill))

    def on_clean_finished(self, killed_count, total_attempted):
        self.status_label.configure(text=f"Successfully killed {killed_count}/{total_attempted} processes.")
        self.refresh_btn.configure(state="normal")
        self.reset_btn.configure(state="normal")
        self.end_sel_btn.configure(state="normal")
        self.refresh_list_threaded()

if __name__ == "__main__":
    ctk.set_appearance_mode("Dark")
    ctk.set_default_color_theme("blue")
    app = App()
    app.mainloop()
