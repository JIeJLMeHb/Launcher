import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import shutil
import json
from datetime import datetime
from utils import InsecureSession
import ttkbootstrap as ttkb
from ttkbootstrap.constants import *

class BaseTab:
    def __init__(self, parent, launcher):
        self.launcher = launcher
        self.frame = ttk.Frame(parent)

class MainTab(BaseTab):
    def __init__(self, parent, launcher):
        super().__init__(parent, launcher)
        self.setup_tab()
    
    def setup_tab(self):
        main_container = ttk.Frame(self.frame)
        main_container.pack(fill="both", expand=True)
        
        canvas = tk.Canvas(main_container, bg='#2b2b2b', highlightthickness=0)
        scrollbar = ttk.Scrollbar(main_container, orient="vertical", command=canvas.yview)
        self.scrollable_frame = ttk.Frame(canvas)
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        warning_label = ttk.Label(self.scrollable_frame, 
                       text="ВНИМАНИЕ: SSL проверка отключена!", 
                       bootstyle="danger",
                       font=("Segoe UI", 10, "bold"))
        warning_label.pack(pady=10, padx=20)
        
        self.setup_version_block()
        self.setup_account_block()
        self.setup_progress_block()
        self.setup_modpack_block()
        self.setup_control_block()
        self.setup_log_block()
        self.setup_status_bar()
    
    def setup_version_block(self):
        version_block = ttk.LabelFrame(self.scrollable_frame, text="Выбор версии", padding=15)
        version_block.pack(fill="x", padx=20, pady=10)
        
        version_frame = ttk.Frame(version_block)
        version_frame.pack(fill="x", pady=5)
        
        ttk.Label(version_frame, text="Версия Minecraft:").pack(side="left", padx=(0, 10))
        self.version_var = tk.StringVar()
        self.version_combobox = ttk.Combobox(version_frame, 
                                           textvariable=self.version_var, 
                                           state="readonly", 
                                           width=30)
        self.version_combobox.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.version_combobox.bind("<<ComboboxSelected>>", self.on_minecraft_version_changed)
        
        self.refresh_button = ttk.Button(version_frame, 
                                       text="🔄", 
                                       width=3,
                                       command=self.launcher.version_manager.refresh_versions)
        self.refresh_button.pack(side="left")
        
        modloader_frame = ttk.Frame(version_block)
        modloader_frame.pack(fill="x", pady=5)
        
        ttk.Label(modloader_frame, text="Модлоадер:").pack(side="left", padx=(0, 10))
        self.modloader_var = tk.StringVar(value="Vanilla")
        self.modloader_combobox = ttk.Combobox(modloader_frame, 
                                              textvariable=self.modloader_var,
                                              values=["Vanilla", "Forge", "NeoForge", "Fabric", "Quilt"],
                                              state="readonly", 
                                              width=15)
        self.modloader_combobox.pack(side="left", padx=(0, 10))
        self.modloader_combobox.bind("<<ComboboxSelected>>", self.on_modloader_changed)
        
        ttk.Label(modloader_frame, text="Версия:").pack(side="left", padx=(0, 10))
        self.modloader_version_var = tk.StringVar()
        self.modloader_version_combobox = ttk.Combobox(modloader_frame, 
                                                      textvariable=self.modloader_version_var,
                                                      state="disabled", 
                                                      width=20)
        self.modloader_version_combobox.pack(side="left", fill="x", expand=True)
    
    def setup_account_block(self):
        account_block = ttk.LabelFrame(self.scrollable_frame, text="Данные аккаунта", padding=15)
        account_block.pack(fill="x", padx=20, pady=10)
        
        username_frame = ttk.Frame(account_block)
        username_frame.pack(fill="x", pady=5)
        ttk.Label(username_frame, text="Имя пользователя:").pack(side="left", padx=(0, 10))
        self.username_entry = ttk.Entry(username_frame, width=30)
        self.username_entry.insert(0, "Player")
        self.username_entry.pack(side="left", fill="x", expand=True)
        
        uuid_frame = ttk.Frame(account_block)
        uuid_frame.pack(fill="x", pady=5)
        ttk.Label(uuid_frame, text="UUID (опционально):").pack(side="left", padx=(0, 10))
        self.uuid_entry = ttk.Entry(uuid_frame, width=40)
        self.uuid_entry.pack(side="left", fill="x", expand=True)
        
        token_frame = ttk.Frame(account_block)
        token_frame.pack(fill="x", pady=5)
        ttk.Label(token_frame, text="Token (опционально):").pack(side="left", padx=(0, 10))
        self.token_entry = ttk.Entry(token_frame, width=40, show="*")
        self.token_entry.pack(side="left", fill="x", expand=True)
        
        self.show_token_var = tk.BooleanVar()
        self.show_token_check = ttk.Checkbutton(token_frame, 
                                              text="Показать", 
                                              variable=self.show_token_var,
                                              command=self.toggle_token_visibility)
        self.show_token_check.pack(side="left", padx=(10, 0))
    
    def setup_progress_block(self):
        progress_block = ttk.LabelFrame(self.scrollable_frame, text="Прогресс установки", padding=15)
        progress_block.pack(fill="x", padx=20, pady=10)
        
        self.progress_var = tk.DoubleVar()
        self.progress = ttk.Progressbar(progress_block, 
                                      mode='determinate',
                                      variable=self.progress_var,
                                      length=100)
        self.progress.pack(fill="x", pady=5)
        
        self.progress_label = ttk.Label(progress_block, text="Готов к установке")
        self.progress_label.pack()
    
    def setup_modpack_block(self):
        modpack_block = ttk.LabelFrame(self.scrollable_frame, text="Быстрый запуск модпака", padding=15)
        modpack_block.pack(fill="x", padx=20, pady=10)
        
        modpack_frame = ttk.Frame(modpack_block)
        modpack_frame.pack(fill="x", pady=5)
        
        ttk.Label(modpack_frame, text="Выберите модпак:").pack(side="left", padx=(0, 10))
        
        self.launcher.modpack_selector_var = tk.StringVar()
        self.launcher.modpack_selector = ttk.Combobox(modpack_frame, 
                                        textvariable=self.launcher.modpack_selector_var,
                                        state="readonly", 
                                        width=25)
        self.launcher.modpack_selector.pack(side="left", padx=(0, 10))
        self.launcher.modpack_selector.bind("<<ComboboxSelected>>", 
                                          self.launcher.on_modpack_selected_in_main_tab)
        
        self.quick_launch_button = ttk.Button(modpack_frame,
                                        text="🚀 Быстрый запуск",
                                        command=self.launcher.quick_launch_modpack,
                                        bootstyle="warning",
                                        padding=(15, 5))
        self.quick_launch_button.pack(side="left", padx=5)
        
        refresh_selector_button = ttk.Button(modpack_frame,
                                        text="🔄",
                                        width=3,
                                        command=self.launcher.refresh_modpack_selector)
        refresh_selector_button.pack(side="left")
        
        self.launcher.modpack_info_label = ttk.Label(modpack_block, 
                                        text="Модпак не выбран",
                                        font=("Segoe UI", 9))
        self.launcher.modpack_info_label.pack(anchor="w", pady=(5, 0))
    
    def setup_control_block(self):
        control_block = ttk.Frame(self.scrollable_frame)
        control_block.pack(fill="x", padx=20, pady=10)
        
        self.install_button = ttk.Button(control_block,
                                    text="Установить",
                                    command=self.launcher.version_manager.install_version,
                                    bootstyle="primary",
                                    padding=(20, 10))
        self.install_button.pack(side="left", padx=(0, 10))
        
        self.launch_button = ttk.Button(control_block,
                             text="🚀 Запуск Minecraft",
                             command=self.launcher.version_manager.launch_minecraft,
                             bootstyle="success",
                             padding=(20, 10))
        self.launch_button.pack(side="left")
    
    def setup_log_block(self):
        log_block = ttk.LabelFrame(self.scrollable_frame, text="Логи установки", padding=10)
        log_block.pack(fill="both", expand=True, padx=20, pady=10)
        
        self.log_text = tk.Text(log_block, 
                              height=12,
                              bg='#3c3c3c',
                              fg='#ffffff',
                              insertbackground='white',
                              wrap="word",
                              font=("Consolas", 9))
        
        scrollbar = ttk.Scrollbar(log_block, command=self.log_text.yview)
        self.log_text.config(yscrollcommand=scrollbar.set)
        
        self.log_text.pack(side="left", fill="both", expand=True, padx=(0, 5))
        scrollbar.pack(side="right", fill="y")
    
    def setup_status_bar(self):
        status_frame = ttk.Frame(self.scrollable_frame)
        status_frame.pack(fill="x", padx=20, pady=(0, 10))
        
        self.status_var = tk.StringVar(value="Готов к работе")
        status_bar = ttk.Label(status_frame, 
                             textvariable=self.status_var, 
                             relief="sunken", 
                             anchor="w",
                             padding=5,
                             background='#3c3c3c',
                             foreground='#ffffff')
        status_bar.pack(fill="x")
    
    def toggle_token_visibility(self):
        if self.show_token_var.get():
            self.token_entry.config(show="")
        else:
            self.token_entry.config(show="*")
    
    def log(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)
        self.launcher.root.update_idletasks()
    
    def set_status(self, message):
        self.status_var.set(message)
        self.launcher.root.update_idletasks()
    
    def update_progress(self, value, max_value=None):
        if max_value is not None and max_value > 0:
            progress_percent = (value / max_value)
            self.progress_var.set(progress_percent)
            self.progress_label.config(text=f"Прогресс: {progress_percent:.1f}%")
        else:
            self.progress_var.set(value)
            self.progress_label.config(text=f"Прогресс: {value:.1f}%")
        
        self.launcher.root.update_idletasks()
    
    def on_minecraft_version_changed(self, event=None):
        selected_version = self.version_var.get()
        modloader = self.modloader_var.get()
        
        if modloader != "Vanilla" and selected_version:
            self.update_modloader_versions_for_minecraft(selected_version, modloader)
    
    def on_modloader_changed(self, event=None):
        modloader = self.modloader_var.get()
        minecraft_version = self.version_var.get()
        
        if modloader == "Vanilla":
            self.modloader_version_combobox['values'] = []
            self.modloader_version_var.set("")
            self.modloader_version_combobox.config(state="disabled")
        else:
            self.modloader_version_combobox.config(state="readonly")
            if minecraft_version:
                self.update_modloader_versions_for_minecraft(minecraft_version, modloader)
    
    def update_modloader_versions_for_minecraft(self, minecraft_version, modloader_type):
        try:
            versions = []
            
            if modloader_type == "Forge":
                for version in self.launcher.version_manager.modloader_versions.get("Forge", []):
                    if version.startswith(minecraft_version):
                        versions.append(version)
            
            elif modloader_type == "NeoForge":
                for version in self.launcher.version_manager.modloader_versions.get("NeoForge", []):
                    if minecraft_version in version:
                        versions.append(version)
            
            elif modloader_type == "Fabric":
                versions = self.launcher.version_manager.modloader_versions.get("Fabric", [])[:20]
            
            elif modloader_type == "Quilt":
                versions = ["Последняя версия"]
            
            if not versions:
                versions = ["Автоматический выбор"]
            
            self.modloader_version_combobox['values'] = versions
            if versions:
                self.modloader_version_combobox.set(versions[0])
            
            self.log(f"Найдено {len(versions)} версий {modloader_type} для Minecraft {minecraft_version}")
            
        except Exception as e:
            self.log(f"Ошибка при фильтрации версий {modloader_type}: {str(e)}")
            self.modloader_version_combobox['values'] = ["Автоматический выбор"]
            self.modloader_version_combobox.set("Автоматический выбор")

class ModsTab(BaseTab):
    def __init__(self, parent, launcher):
        super().__init__(parent, launcher)
        self.setup_tab()
    
    def setup_tab(self):
        main_container = ttk.Frame(self.frame)
        main_container.pack(fill="both", expand=True, padx=10, pady=10)
        
        control_frame = ttk.LabelFrame(main_container, text="Управление модами", padding=10)
        control_frame.pack(fill="x", pady=(0, 10))
        
        self.setup_buttons(control_frame)
        
        content_container = ttk.Frame(main_container)
        content_container.pack(fill="both", expand=True)
        
        paned = tk.PanedWindow(content_container, orient=tk.HORIZONTAL, bg='#2b2b2b', sashwidth=5)
        paned.pack(fill="both", expand=True)
        
        list_frame = ttk.LabelFrame(paned, text="Список модов", padding=10)
        self.setup_mods_tree(list_frame)
        
        info_frame = ttk.LabelFrame(paned, text="Информация о моде", padding=10)
        self.setup_mod_info_text(info_frame)
        
        paned.add(list_frame, width=500, minsize=300)
        paned.add(info_frame, width=300, minsize=200)
        
        self.mods_tree.bind("<<TreeviewSelect>>", self.on_mod_selected)
        
        self.refresh_mods_list()
    
    def setup_buttons(self, parent):
        button_frame = ttk.Frame(parent)
        button_frame.pack()
        
        self.add_mod_button = ttk.Button(button_frame,
                            text="📁 Добавить из файла",
                            command=self.add_mod_from_file,
                            bootstyle="primary",
                            padding=(15, 5))
        self.add_mod_button.pack(side="left", padx=5)
        
        self.add_mod_url_button = ttk.Button(button_frame,
                                text="🔗 Добавить по ссылке",
                                command=self.add_mod_from_url,
                                bootstyle="primary",
                                padding=(15, 5))
        self.add_mod_url_button.pack(side="left", padx=5)
        
        self.remove_mod_button = ttk.Button(button_frame,
                                text="🗑️ Удалить выбранный",
                                command=self.remove_selected_mod,
                                bootstyle="danger",
                                padding=(15, 5))
        self.remove_mod_button.pack(side="left", padx=5)
        
        self.clear_mods_button = ttk.Button(button_frame,
                                text="🧹 Очистить все",
                                command=self.clear_all_mods,
                                bootstyle="danger",
                                padding=(15, 5))
        self.clear_mods_button.pack(side="left", padx=5)
        
        self.refresh_mods_button = ttk.Button(button_frame,
                                text="🔄 Обновить",
                                command=self.refresh_mods_list,
                                bootstyle="info",
                                padding=(15, 5))
        self.refresh_mods_button.pack(side="left", padx=5)
        
        self.current_modpack_label = ttk.Label(parent, 
                                            text="Текущий модпак: Не выбран",
                                            font=("Segoe UI", 9, "italic"))
        self.current_modpack_label.pack(pady=(10, 0))
    
    def setup_mods_tree(self, parent):
        columns = ("Название", "Версия", "Размер", "Файл")
        self.mods_tree = ttk.Treeview(parent, columns=columns, show="headings", height=15)
        
        self.mods_tree.heading("Название", text="Название", anchor="w")
        self.mods_tree.heading("Версия", text="Версия", anchor="center")
        self.mods_tree.heading("Размер", text="Размер", anchor="center")
        self.mods_tree.heading("Файл", text="Файл", anchor="w")
        
        self.mods_tree.column("Название", width=200)
        self.mods_tree.column("Версия", width=80, anchor="center")
        self.mods_tree.column("Размер", width=80, anchor="center")
        self.mods_tree.column("Файл", width=150)
        
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=self.mods_tree.yview)
        self.mods_tree.configure(yscrollcommand=scrollbar.set)
        
        self.mods_tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
    
    def setup_mod_info_text(self, parent):
        self.mod_info_text = tk.Text(parent, 
                                height=20, 
                                wrap="word",
                                bg='#3c3c3c',
                                fg='#ffffff',
                                insertbackground='white',
                                font=("Segoe UI", 9),
                                width=40)
        mod_info_scrollbar = ttk.Scrollbar(parent, command=self.mod_info_text.yview)
        self.mod_info_text.config(yscrollcommand=mod_info_scrollbar.set)
        
        self.mod_info_text.pack(side="left", fill="both", expand=True)
        mod_info_scrollbar.pack(side="right", fill="y")
    
    def refresh_mods_list(self):
        try:
            for item in self.mods_tree.get_children():
                self.mods_tree.delete(item)
            
            if self.launcher.current_modpack:
                mods_dir = os.path.join(self.launcher.MODPACKS_DIR, self.launcher.current_modpack, "mods")
            else:
                mods_dir = os.path.join(self.launcher.MINECRAFT_DIR, "mods")
            
            if not os.path.exists(mods_dir):
                os.makedirs(mods_dir, exist_ok=True)
                return
            
            mod_files = [f for f in os.listdir(mods_dir) if f.endswith('.jar')]
            
            for mod_file in mod_files:
                mod_path = os.path.join(mods_dir, mod_file)
                mod_size = os.path.getsize(mod_path)
                
                mod_name = mod_file
                mod_version = "Неизвестно"
                
                parts = mod_file.replace('.jar', '').split('-')
                if len(parts) >= 2:
                    mod_name = parts[0]
                    mod_version = parts[-1]
                
                if mod_size > 1024 * 1024:
                    size_str = f"{mod_size / 1024 / 1024:.1f} MB"
                else:
                    size_str = f"{mod_size / 1024:.0f} KB"
                
                self.mods_tree.insert("", "end", values=(mod_name, mod_version, size_str, mod_file))
            
            self.launcher.main_tab.log(f"Загружено {len(mod_files)} модов")
            
        except Exception as e:
            self.launcher.main_tab.log(f"Ошибка при обновлении списка модов: {str(e)}")
    
    def add_mod_from_file(self):
        try:
            file_path = filedialog.askopenfilename(
                title="Выберите файл мода",
                filetypes=[("JAR файлы", "*.jar"), ("Все файлы", "*.*")]
            )
            
            if file_path:
                mod_name = os.path.basename(file_path)
                
                if self.launcher.current_modpack:
                    dest_dir = os.path.join(self.launcher.MODPACKS_DIR, self.launcher.current_modpack, "mods")
                else:
                    dest_dir = os.path.join(self.launcher.MINECRAFT_DIR, "mods")
                
                os.makedirs(dest_dir, exist_ok=True)
                dest_path = os.path.join(dest_dir, mod_name)
                
                shutil.copy2(file_path, dest_path)
                self.launcher.main_tab.log(f"Мод {mod_name} добавлен")
                self.refresh_mods_list()
                
        except Exception as e:
            self.launcher.main_tab.log(f"Ошибка при добавлении мода: {str(e)}")
            messagebox.showerror("Ошибка", f"Не удалось добавить мод: {str(e)}")
    
    def add_mod_from_url(self):
        try:
            url_dialog = tk.Toplevel(self.launcher.root)
            url_dialog.title("Добавить мод по ссылке")
            url_dialog.geometry("500x150")
            url_dialog.configure(bg='#2b2b2b')
            url_dialog.transient(self.launcher.root)
            url_dialog.grab_set()
            
            url_dialog.update_idletasks()
            x = self.launcher.root.winfo_x() + (self.launcher.root.winfo_width() - url_dialog.winfo_width()) // 2
            y = self.launcher.root.winfo_y() + (self.launcher.root.winfo_height() - url_dialog.winfo_height()) // 2
            url_dialog.geometry(f"+{x}+{y}")
            
            tk.Label(url_dialog, 
                    text="Введите URL мода:", 
                    bg='#2b2b2b', 
                    fg='white').pack(pady=10)
            
            url_entry = ttk.Entry(url_dialog, width=60)
            url_entry.pack(pady=5, padx=20)
            
            def download_mod():
                url = url_entry.get().strip()
                if not url:
                    messagebox.showwarning("Внимание", "Введите URL")
                    return
                
                try:
                    self.launcher.main_tab.log(f"Загрузка мода из {url}...")
                    session = InsecureSession()
                    response = session.get(url, stream=True, timeout=30)
                    
                    if 'Content-Disposition' in response.headers:
                        content_disposition = response.headers['Content-Disposition']
                        filename = content_disposition.split('filename=')[1].strip('"')
                    else:
                        filename = os.path.basename(url)
                    
                    if not filename.endswith('.jar'):
                        filename += '.jar'
                    
                    if self.launcher.current_modpack:
                        dest_dir = os.path.join(self.launcher.MODPACKS_DIR, self.launcher.current_modpack, "mods")
                    else:
                        dest_dir = os.path.join(self.launcher.MINECRAFT_DIR, "mods")
                    
                    os.makedirs(dest_dir, exist_ok=True)
                    dest_path = os.path.join(dest_dir, filename)
                    
                    total_size = int(response.headers.get('content-length', 0))
                    downloaded = 0
                    
                    with open(dest_path, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)
                                downloaded += len(chunk)
                                if total_size > 0:
                                    progress = (downloaded / total_size) * 100
                                    self.launcher.root.after(0, self.launcher.main_tab.update_progress, progress)
                    
                    self.launcher.main_tab.log(f"Мод {filename} успешно загружен")
                    self.refresh_mods_list()
                    url_dialog.destroy()
                    
                except Exception as e:
                    self.launcher.main_tab.log(f"Ошибка при загрузке мода: {str(e)}")
                    messagebox.showerror("Ошибка", f"Не удалось загрузить мод: {str(e)}")
            
            button_frame = ttk.Frame(url_dialog)
            button_frame.pack(pady=10)
            
            ttk.Button(button_frame, text="Загрузить", command=download_mod).pack(side="left", padx=5)
            ttk.Button(button_frame, text="Отмена", command=url_dialog.destroy).pack(side="left", padx=5)
            
        except Exception as e:
            self.launcher.main_tab.log(f"Ошибка: {str(e)}")
    
    def remove_selected_mod(self):
        try:
            selection = self.mods_tree.selection()
            if not selection:
                messagebox.showinfo("Информация", "Выберите мод для удаления")
                return
            
            item = self.mods_tree.item(selection[0])
            mod_filename = item['values'][3]
            
            if self.launcher.current_modpack:
                mod_dir = os.path.join(self.launcher.MODPACKS_DIR, self.launcher.current_modpack, "mods")
            else:
                mod_dir = os.path.join(self.launcher.MINECRAFT_DIR, "mods")
            
            mod_path = os.path.join(mod_dir, mod_filename)
            
            if os.path.exists(mod_path):
                os.remove(mod_path)
                self.launcher.main_tab.log(f"Мод {mod_filename} удален")
                self.refresh_mods_list()
            else:
                messagebox.showwarning("Внимание", "Файл мода не найден")
                
        except Exception as e:
            self.launcher.main_tab.log(f"Ошибка при удалении мода: {str(e)}")
            messagebox.showerror("Ошибка", f"Не удалось удалить мод: {str(e)}")
    
    def clear_all_mods(self):
        try:
            if self.launcher.current_modpack:
                mod_dir = os.path.join(self.launcher.MODPACKS_DIR, self.launcher.current_modpack, "mods")
            else:
                mod_dir = os.path.join(self.launcher.MINECRAFT_DIR, "mods")
            
            if not os.path.exists(mod_dir):
                return
            
            if messagebox.askyesno("Подтверждение", "Удалить все моды?"):
                for file in os.listdir(mod_dir):
                    if file.endswith('.jar'):
                        os.remove(os.path.join(mod_dir, file))
                
                self.launcher.main_tab.log("Все моды удалены")
                self.refresh_mods_list()
                
        except Exception as e:
            self.launcher.main_tab.log(f"Ошибка при очистке модов: {str(e)}")
    
    def on_mod_selected(self, event):
        try:
            selection = self.mods_tree.selection()
            if not selection:
                return
            
            item = self.mods_tree.item(selection[0])
            mod_filename = item['values'][3]
            
            if self.launcher.current_modpack:
                mod_dir = os.path.join(self.launcher.MODPACKS_DIR, self.launcher.current_modpack, "mods")
            else:
                mod_dir = os.path.join(self.launcher.MINECRAFT_DIR, "mods")
            
            mod_path = os.path.join(mod_dir, mod_filename)
            
            self.mod_info_text.delete(1.0, tk.END)
            
            if os.path.exists(mod_path):
                mod_size = os.path.getsize(mod_path)
                mod_time = os.path.getmtime(mod_path)
                
                info_text = f"📁 Имя файла: {mod_filename}\n\n"
                info_text += f"📊 Размер: {item['values'][2]}\n"
                info_text += f"📅 Дата изменения: {datetime.fromtimestamp(mod_time).strftime('%Y-%m-%d %H:%M:%S')}\n"
                info_text += f"📍 Путь: {mod_path}\n\n"
                
                try:
                    import zipfile
                    with zipfile.ZipFile(mod_path, 'r') as zip_ref:
                        for file_info in zip_ref.infolist():
                            filename = file_info.filename
                            if 'fabric.mod.json' in filename or 'mods.toml' in filename or 'mcmod.info' in filename:
                                info_text += f"📄 Конфигурационный файл: {filename}\n"
                                break
                except Exception:
                    pass
                
                self.mod_info_text.insert(1.0, info_text)
            
        except Exception as e:
            self.launcher.main_tab.log(f"Ошибка при получении информации о моде: {str(e)}")

class ModpacksTab(BaseTab):
    def __init__(self, parent, launcher):
        super().__init__(parent, launcher)
        self.setup_tab()
    
    def setup_tab(self):
        main_container = ttk.Frame(self.frame)
        main_container.pack(fill="both", expand=True, padx=10, pady=10)
        
        control_frame = ttk.LabelFrame(main_container, text="Управление модпаками", padding=10)
        control_frame.pack(fill="x", pady=(0, 10))
        
        self.setup_buttons(control_frame)
        
        content_container = ttk.Frame(main_container)
        content_container.pack(fill="both", expand=True, pady=(0, 10))
        
        paned = tk.PanedWindow(content_container, orient=tk.HORIZONTAL, bg='#2b2b2b', sashwidth=5)
        paned.pack(fill="both", expand=True)
        
        list_frame = ttk.LabelFrame(paned, text="Список модпаков", padding=10)
        self.setup_modpacks_tree(list_frame)
        
        info_frame = ttk.LabelFrame(paned, text="Информация о модпаке", padding=10)
        self.setup_modpack_info_text(info_frame)
        
        paned.add(list_frame, width=550, minsize=400)
        paned.add(info_frame, width=350, minsize=250)
        
        self.modpacks_tree.bind("<<TreeviewSelect>>", self.on_modpack_selected)
        
        self.launcher.refresh_modpacks_list()
    
    def setup_buttons(self, parent):
        button_frame = ttk.Frame(parent)
        button_frame.pack()
        
        self.create_modpack_button = ttk.Button(button_frame,
                                    text="➕ Создать модпак",
                                    command=self.launcher.create_modpack_dialog,
                                    bootstyle="success",
                                    padding=(15, 5))
        self.create_modpack_button.pack(side="left", padx=5)
        
        self.delete_modpack_button = ttk.Button(button_frame,
                                    text="🗑️ Удалить модпак",
                                    command=self.delete_modpack,
                                    bootstyle="danger",
                                    padding=(15, 5))
        self.delete_modpack_button.pack(side="left", padx=5)
        
        self.export_modpack_button = ttk.Button(button_frame,
                                    text="📤 Экспорт модпака",
                                    command=self.launcher.export_modpack,
                                    bootstyle="info",
                                    padding=(15, 5))
        self.export_modpack_button.pack(side="left", padx=5)
        
        self.refresh_modpacks_button = ttk.Button(button_frame,
                                    text="🔄 Обновить",
                                    command=self.launcher.refresh_modpacks_list,
                                    bootstyle="info",
                                    padding=(15, 5))
        self.refresh_modpacks_button.pack(side="left", padx=5)
    
    def setup_modpacks_tree(self, parent):
        columns = ("Название", "Версия игры", "Модлоадер", "Кол-во модов", "Дата создания")
        self.modpacks_tree = ttk.Treeview(parent, columns=columns, show="headings", height=10)
        
        self.modpacks_tree.heading("Название", text="Название", anchor="w")
        self.modpacks_tree.heading("Версия игры", text="Версия игры", anchor="center")
        self.modpacks_tree.heading("Модлоадер", text="Модлоадер", anchor="center")
        self.modpacks_tree.heading("Кол-во модов", text="Кол-во модов", anchor="center")
        self.modpacks_tree.heading("Дата создания", text="Дата создания", anchor="center")
        
        self.modpacks_tree.column("Название", width=150)
        self.modpacks_tree.column("Версия игры", width=100, anchor="center")
        self.modpacks_tree.column("Модлоадер", width=100, anchor="center")
        self.modpacks_tree.column("Кол-во модов", width=80, anchor="center")
        self.modpacks_tree.column("Дата создания", width=120, anchor="center")
        
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=self.modpacks_tree.yview)
        self.modpacks_tree.configure(yscrollcommand=scrollbar.set)
        
        self.modpacks_tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
    
    def setup_modpack_info_text(self, parent):
        self.modpack_info_text = tk.Text(parent)
        modpack_info_scrollbar = ttk.Scrollbar(parent, command=self.modpack_info_text.yview)
        self.modpack_info_text.config(yscrollcommand=modpack_info_scrollbar.set)
        
        self.modpack_info_text.pack(side="left", fill="both", expand=True)
        modpack_info_scrollbar.pack(side="right", fill="y")
    
    def create_modpack_dialog(self):
        try:
            dialog = tk.Toplevel(self.launcher.root)
            dialog.title("Создание нового модпака")
            dialog.geometry("400x400")
            dialog.transient(self.launcher.root)
            dialog.grab_set()
            
            dialog.update_idletasks()
            x = self.launcher.root.winfo_x() + (self.launcher.root.winfo_width() - dialog.winfo_width()) // 2
            y = self.launcher.root.winfo_y() + (self.launcher.root.winfo_height() - dialog.winfo_height()) // 2
            dialog.geometry(f"+{x}+{y}")
            
            tk.Label(dialog, 
                    text="Создание нового модпака")
            
            name_frame = ttk.Frame(dialog)
            name_frame.pack(fill="x", padx=30, pady=10)
            
            ttk.Label(name_frame, text="Название модпака:").pack(anchor="w")
            name_entry = ttk.Entry(name_frame)
            name_entry.pack(fill="x", pady=5)
            
            version_frame = ttk.Frame(dialog)
            version_frame.pack(fill="x", padx=30, pady=10)
            
            ttk.Label(version_frame, text="Версия Minecraft:").pack(anchor="w")
            version_var = tk.StringVar()
            version_combobox = ttk.Combobox(version_frame, textvariable=version_var, 
                                        values=self.launcher.main_tab.version_combobox['values'],
                                        state="readonly")
            version_combobox.pack(fill="x", pady=5)
            if self.launcher.main_tab.version_var.get():
                version_combobox.set(self.launcher.main_tab.version_var.get())
            
            modloader_frame = ttk.Frame(dialog)
            modloader_frame.pack(fill="x", padx=30, pady=10)
            
            ttk.Label(modloader_frame, text="Модлоадер:").pack(anchor="w")
            modloader_var = tk.StringVar(value="Vanilla")
            modloader_combobox = ttk.Combobox(modloader_frame, textvariable=modloader_var,
                                            values=["Vanilla", "Forge", "NeoForge", "Fabric", "Quilt"],
                                            state="readonly")
            modloader_combobox.pack(fill="x", pady=5)
            
            modloader_version_frame = ttk.Frame(dialog)
            modloader_version_frame.pack(fill="x", padx=30, pady=10)
            
            ttk.Label(modloader_version_frame, text="Версия модлоадера:").pack(anchor="w")
            modloader_version_var = tk.StringVar()
            modloader_version_combobox = ttk.Combobox(modloader_version_frame, 
                                                    textvariable=modloader_version_var,
                                                    state="readonly")
            modloader_version_combobox.pack(fill="x", pady=5)
            
            def update_modloader_versions(event=None):
                selected_modloader = modloader_var.get()
                selected_version = version_var.get()
                
                if selected_modloader == "Vanilla" or not selected_version:
                    modloader_version_combobox['values'] = []
                    modloader_version_var.set("")
                    modloader_version_combobox.config(state="disabled")
                else:
                    modloader_version_combobox.config(state="readonly")
                    versions = []
                    
                    if selected_modloader == "Forge":
                        for version in self.launcher.version_manager.modloader_versions.get("Forge", []):
                            if version.startswith(selected_version):
                                versions.append(version)
                    
                    elif selected_modloader == "NeoForge":
                        for version in self.launcher.version_manager.modloader_versions.get("NeoForge", []):
                            if selected_version in version:
                                versions.append(version)
                    
                    elif selected_modloader == "Fabric":
                        versions = self.launcher.version_manager.modloader_versions.get("Fabric", [])[:10]
                    
                    elif selected_modloader == "Quilt":
                        versions = ["Последняя версия"]
                    
                    if not versions:
                        versions = ["Автоматический выбор"]
                    
                    modloader_version_combobox['values'] = versions
                    if versions:
                        modloader_version_combobox.set(versions[0])
            
            version_combobox.bind("<<ComboboxSelected>>", update_modloader_versions)
            modloader_combobox.bind("<<ComboboxSelected>>", update_modloader_versions)
            
            desc_frame = ttk.Frame(dialog)
            desc_frame.pack(fill="x", padx=30, pady=10)
            
            ttk.Label(desc_frame, text="Описание (опционально):").pack(anchor="w")
            desc_entry = tk.Text(desc_frame, height=3, width=40)
            desc_entry.pack(fill="x", pady=5)
            
            def create_modpack():
                name = name_entry.get().strip()
                if not name:
                    messagebox.showwarning("Внимание", "Введите название модпака")
                    return
                
                safe_name = "".join(c for c in name if c.isalnum() or c in (' ', '-', '_')).strip()
                if not safe_name:
                    safe_name = "new_modpack"
                
                minecraft_version = version_var.get()
                modloader = modloader_var.get()
                modloader_version = modloader_version_var.get()
                
                self.launcher.create_modpack(safe_name, desc_entry.get("1.0", tk.END).strip(), 
                                            minecraft_version, modloader)
                dialog.destroy()
            
            button_frame = ttk.Frame(dialog)
            button_frame.pack(pady=10)
            
            ttk.Button(button_frame, text="Создать", command=create_modpack).pack(side="left", padx=5)
            ttk.Button(button_frame, text="Отмена", command=dialog.destroy).pack(side="left", padx=5)
            
            update_modloader_versions()
            
        except Exception as e:
            self.launcher.main_tab.log(f"Ошибка при создании диалога: {str(e)}")
    
    def delete_modpack(self):
        try:
            selection = self.modpacks_tree.selection()
            if not selection:
                messagebox.showinfo("Информация", "Выберите модпак для удаления")
                return
            
            item = self.modpacks_tree.item(selection[0])
            modpack_name = item['values'][0]
            
            if messagebox.askyesno("Подтверждение", 
                                 f"Удалить модпак '{modpack_name}'?\nЭто действие нельзя отменить!"):
                modpack_path = os.path.join(self.launcher.MODPACKS_DIR, modpack_name)
                
                if os.path.exists(modpack_path):
                    shutil.rmtree(modpack_path)
                    
                    if self.launcher.current_modpack == modpack_name:
                        self.launcher.current_modpack = None
                        self.launcher.mods_tab.current_modpack_label.config(text="Текущий модпак: Не выбран")
                        self.launcher.refresh_mods_list()
                    
                    self.launcher.main_tab.log(f"Модпак '{modpack_name}' удален")
                    self.launcher.refresh_modpacks_list()
                    
        except Exception as e:
            self.launcher.main_tab.log(f"Ошибка при удалении модпака: {str(e)}")
            messagebox.showerror("Ошибка", f"Не удалось удалить модпак: {str(e)}")
    
    def export_modpack(self):
        try:
            selection = self.modpacks_tree.selection()
            if not selection:
                messagebox.showinfo("Информация", "Выберите модпак для экспорта")
                return
            
            item = self.modpacks_tree.item(selection[0])
            modpack_name = item['values'][0]
            
            filename = filedialog.asksaveasfilename(
                title="Экспорт модпака",
                defaultextension=".zip",
                filetypes=[("ZIP архив", "*.zip"), ("Все файлы", "*.*")],
                initialfile=f"{modpack_name}.zip"
            )
            
            if filename:
                modpack_path = os.path.join(self.launcher.MODPACKS_DIR, modpack_name)
                
                if os.path.exists(modpack_path):
                    shutil.make_archive(filename.replace('.zip', ''), 'zip', modpack_path)
                    self.launcher.main_tab.log(f"Модпак '{modpack_name}' экспортирован в {filename}")
                    messagebox.showinfo("Успех", f"Модпак успешно экспортирован!")
                    
        except Exception as e:
            self.launcher.main_tab.log(f"Ошибка при экспорте модпака: {str(e)}")
            messagebox.showerror("Ошибка", f"Не удалось экспортировать модпак: {str(e)}")
    
    def on_modpack_selected(self, event):
        try:
            selection = self.modpacks_tree.selection()
            if not selection:
                return
            
            item = self.modpacks_tree.item(selection[0])
            modpack_name = item['values'][0]
            
            info_file = os.path.join(self.launcher.MODPACKS_DIR, modpack_name, "modpack_info.json")
            
            if os.path.exists(info_file):
                with open(info_file, 'r', encoding='utf-8') as f:
                    info = json.load(f)
                
                info_text = f"📦 Модпак: {info.get('name', modpack_name)}\n\n"
                info_text += f"📝 Описание: {info.get('description', 'Нет описания')}\n"
                info_text += f"🎮 Версия Minecraft: {info.get('minecraft_version', 'Не указана')}\n"
                info_text += f"🔧 Модлоадер: {info.get('modloader', 'Не указан')}\n"
                info_text += f"📅 Создан: {info.get('created', 'Не указана')}\n"
                
                mods_dir = os.path.join(self.launcher.MODPACKS_DIR, modpack_name, "mods")
                mod_count = 0
                if os.path.exists(mods_dir):
                    mod_count = len([f for f in os.listdir(mods_dir) if f.endswith('.jar')])
                
                info_text += f"📦 Количество модов: {mod_count}\n"
                
                self.modpack_info_text.delete(1.0, tk.END)
                self.modpack_info_text.insert(1.0, info_text)
                
                self.launcher.current_modpack = modpack_name
                self.launcher.mods_tab.current_modpack_label.config(text=f"Текущий модпак: {info.get('name', modpack_name)}")
                
                self.launcher.update_modpack_info()
                self.launcher.refresh_mods_list()
            
        except Exception as e:
            self.launcher.main_tab.log(f"Ошибка при получении информации о модпаке: {str(e)}")