import tkinter as tk
from tkinter import ttk, messagebox
import json
import logging
from cryptography.fernet import Fernet
import os

logger = logging.getLogger("Lucky.SettingsGUI")

class SettingsGUI:
    def __init__(self, config_path="config.json"):
        self.config_path = config_path
        with open(self.config_path, "r", encoding="utf-8") as f:
            self.config = json.load(f)
            
        self.root = tk.Tk()
        self.root.title("Lucky Settings V2")
        self.root.geometry("600x500")
        
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill='both', expand=True, padx=10, pady=10)
        
        self._build_general_tab()
        self._build_security_tab()
        self._build_custom_tab()
        self._build_website_tab()
        
        btn_frame = ttk.Frame(self.root)
        btn_frame.pack(fill='x', padx=10, pady=5)
        
        ttk.Button(btn_frame, text="Save & Apply", command=self.save_config).pack(side='right')
        ttk.Button(btn_frame, text="Cancel", command=self.root.destroy).pack(side='right', padx=5)

    def _build_general_tab(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="General")
        
        ttk.Label(tab, text="Wake Word Threshold:").grid(row=0, column=0, sticky='w', pady=10)
        self.thresh_var = tk.DoubleVar(value=self.config.get("wake_word_threshold", 0.5))
        ttk.Scale(tab, from_=0.3, to=0.8, variable=self.thresh_var, orient='horizontal').grid(row=0, column=1, sticky='we')
        
        ttk.Label(tab, text="Language:").grid(row=1, column=0, sticky='w', pady=10)
        self.lang_var = tk.StringVar(value=self.config.get("language", "hi"))
        ttk.Combobox(tab, textvariable=self.lang_var, values=["hi", "en"]).grid(row=1, column=1, sticky='we')
        
        self.beep_var = tk.BooleanVar(value=self.config.get("beep_sound", True))
        ttk.Checkbutton(tab, text="Enable Beep Sound", variable=self.beep_var).grid(row=2, column=0, columnspan=2, sticky='w', pady=10)
        
        self.startup_var = tk.BooleanVar(value=self.config.get("run_on_startup", False))
        ttk.Checkbutton(tab, text="Run on Windows Startup", variable=self.startup_var).grid(row=3, column=0, columnspan=2, sticky='w', pady=10)

        ttk.Label(tab, text="Gemini API Key (optional):").grid(row=4, column=0, sticky='w', pady=10)
        self.gemini_key_var = tk.StringVar(value=self.config.get("gemini_api_key", ""))
        ttk.Entry(tab, textvariable=self.gemini_key_var, show="*").grid(row=4, column=1, sticky='we')
        ttk.Label(
            tab,
            text="AI responses ke liye (offline commands ke liye zaroori nahi)."
        ).grid(row=5, column=0, columnspan=2, sticky='w', pady=(0, 10))

        tab.columnconfigure(1, weight=1)

    def _build_security_tab(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Security")
        
        ttk.Label(tab, text="Set New Pin/Password:").grid(row=0, column=0, sticky='w', pady=10)
        self.pwd_var = tk.StringVar()
        ttk.Entry(tab, textvariable=self.pwd_var, show="*").grid(row=0, column=1, sticky='we')
        ttk.Button(tab, text="Update Password", command=self._update_password).grid(row=1, column=0, columnspan=2, pady=5)
        
        ttk.Label(tab, text="Wrong Command Limit:").grid(row=2, column=0, sticky='w', pady=10)
        self.limit_var = tk.IntVar(value=self.config.get("wrong_command_limit", 3))
        ttk.Entry(tab, textvariable=self.limit_var).grid(row=2, column=1, sticky='we')

    def _build_custom_tab(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Custom Apps")
        
        ttk.Label(tab, text="Add an App Alias (Alias -> .exe Path)").grid(row=0, column=0, columnspan=2, pady=5)
        self.alias_var = tk.StringVar()
        self.path_var = tk.StringVar()
        
        ttk.Label(tab, text="Alias (e.g. word):").grid(row=1, column=0, sticky='w')
        ttk.Entry(tab, textvariable=self.alias_var).grid(row=1, column=1, sticky='we')
        
        ttk.Label(tab, text="Path (e.g. winword.exe):").grid(row=2, column=0, sticky='w')
        ttk.Entry(tab, textvariable=self.path_var).grid(row=2, column=1, sticky='we')
        
        ttk.Button(tab, text="Add App Alias", command=self._add_alias).grid(row=3, column=0, columnspan=2, pady=10)

    def _build_website_tab(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Websites")
        
        ttk.Label(tab, text="Add a Website Alias (Name -> URL)").grid(row=0, column=0, columnspan=2, pady=5)
        self.site_alias_var = tk.StringVar()
        self.url_var = tk.StringVar()
        
        ttk.Label(tab, text="Name (e.g. college site):").grid(row=1, column=0, sticky='w')
        ttk.Entry(tab, textvariable=self.site_alias_var).grid(row=1, column=1, sticky='we')
        
        ttk.Label(tab, text="URL (https://...):").grid(row=2, column=0, sticky='w')
        ttk.Entry(tab, textvariable=self.url_var).grid(row=2, column=1, sticky='we')
        
        ttk.Button(tab, text="Add Website", command=self._add_website).grid(row=3, column=0, columnspan=2, pady=10)

    def _update_password(self):
        pwd = self.pwd_var.get()
        if not pwd: return
        try:
            from actions.system import _get_or_create_key
            from cryptography.fernet import Fernet
            key = _get_or_create_key()
            f = Fernet(key)
            self.config["lock_password_hash"] = f.encrypt(pwd.encode()).decode()
            messagebox.showinfo("Success", "Password Updated!")
        except Exception as e:
            messagebox.showerror("Error", f"Password update failed: {e}")

    def _add_alias(self):
        alias = self.alias_var.get().lower().strip()
        path = self.path_var.get().strip()
        if alias and path:
            if "app_aliases" not in self.config: self.config["app_aliases"] = {}
            self.config["app_aliases"][alias] = path
            messagebox.showinfo("Success", f"Added app alias '{alias}'")

    def _add_website(self):
        alias = self.site_alias_var.get().lower().strip()
        url = self.url_var.get().strip()
        if alias and url:
            if "websites" not in self.config: self.config["websites"] = {}
            self.config["websites"][alias] = url
            messagebox.showinfo("Success", f"Added website '{alias}'")

    def save_config(self):
        self.config["wake_word_threshold"] = self.thresh_var.get()
        self.config["language"] = self.lang_var.get()
        self.config["beep_sound"] = self.beep_var.get()
        self.config["run_on_startup"] = self.startup_var.get()
        self.config["wrong_command_limit"] = self.limit_var.get()
        self.config["gemini_api_key"] = self.gemini_key_var.get().strip()
        
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(self.config, f, indent=2, ensure_ascii=False)
            
        messagebox.showinfo("Saved", "Configuration saved! Setup new hooks via tray restart.")
        self.root.destroy()

def open_settings():
    try:
        app = SettingsGUI()
        app.root.mainloop()
    except Exception as e:
        logger.error(f"Error opening settings GUI: {e}")

if __name__ == "__main__":
    open_settings()
