import tkinter as tk
from tkinter import ttk, messagebox
import os
import json
from datetime import datetime
import shutil
import minecraft_launcher_lib as mclib
import subprocess
import threading
import tempfile
from utils import setup_dark_theme, InsecureSession
from tabs import MainTab, ModsTab, ModpacksTab
from version_manager import VersionManager

class MinecraftLauncher:
    def __init__(self, root):
        self.root = root
        self.root.title("Minecraft Launcher")
        self.root.geometry("680x720")
        self.root.configure(bg='#2b2b2b')
        
        setup_dark_theme()
        
        self.MINECRAFT_DIR = ".minecraft"
        self.MODPACKS_DIR = os.path.join(self.MINECRAFT_DIR, "modpacks")
        self.MODS_CACHE_DIR = os.path.join(self.MINECRAFT_DIR, "mods_cache")
        
        os.makedirs(self.MODPACKS_DIR, exist_ok=True)
        os.makedirs(self.MODS_CACHE_DIR, exist_ok=True)
        
        self.current_modpack = None
        self.version_manager = VersionManager(self)
        
        self.setup_notebook()
        self.version_manager.refresh_versions()
        self.refresh_modpacks_list()
    
    def setup_notebook(self):
        style = ttk.Style()
        style.configure('Custom.TNotebook', background='#2b2b2b', borderwidth=0)
        style.configure('Custom.TNotebook.Tab', 
                    background='#3c3c3c', 
                    foreground='white',
                    padding=[10, 5])
        style.map('Custom.TNotebook.Tab', 
                background=[('selected', '#4a4a4a')],
                foreground=[('selected', 'white')])
        
        self.notebook = ttk.Notebook(self.root, style='Custom.TNotebook')
        self.notebook.pack(fill="both", expand=True, padx=10, pady=10)
        
        self.main_tab = MainTab(self.notebook, self)
        self.mods_tab = ModsTab(self.notebook, self)
        self.modpacks_tab = ModpacksTab(self.notebook, self)
        
        self.notebook.add(self.main_tab.frame, text="Основная")
        self.notebook.add(self.mods_tab.frame, text="Моды")
        self.notebook.add(self.modpacks_tab.frame, text="Модпаки")
    
    def refresh_mods_list(self):
        self.mods_tab.refresh_mods_list()
    
    def add_mod_from_file(self):
        self.mods_tab.add_mod_from_file()
    
    def add_mod_from_url(self):
        self.mods_tab.add_mod_from_url()
    
    def remove_selected_mod(self):
        self.mods_tab.remove_selected_mod()
    
    def clear_all_mods(self):
        self.mods_tab.clear_all_mods()
    
    def refresh_modpacks_list(self):
        try:
            for item in self.modpacks_tab.modpacks_tree.get_children():
                self.modpacks_tab.modpacks_tree.delete(item)
            
            if not os.path.exists(self.MODPACKS_DIR):
                os.makedirs(self.MODPACKS_DIR, exist_ok=True)
                return
            
            modpack_folders = [f for f in os.listdir(self.MODPACKS_DIR) 
                             if os.path.isdir(os.path.join(self.MODPACKS_DIR, f))]
            
            for modpack in modpack_folders:
                modpack_path = os.path.join(self.MODPACKS_DIR, modpack)
                info_file = os.path.join(modpack_path, "modpack_info.json")
                
                if os.path.exists(info_file):
                    try:
                        with open(info_file, 'r', encoding='utf-8') as f:
                            info = json.load(f)
                    except Exception:
                        info = {}
                else:
                    info = {}
                
                mods_dir = os.path.join(modpack_path, "mods")
                mod_count = 0
                if os.path.exists(mods_dir):
                    mod_count = len([f for f in os.listdir(mods_dir) if f.endswith('.jar')])
                
                self.modpacks_tab.modpacks_tree.insert("", "end", values=(
                    info.get('name', modpack),
                    info.get('minecraft_version', 'Не указана'),
                    info.get('modloader', 'Не указан'),
                    str(mod_count),
                    info.get('created', 'Не указана')
                ))
            
            self.main_tab.log(f"Загружено {len(modpack_folders)} модпаков")
            
        except Exception as e:
            self.main_tab.log(f"Ошибка при обновлении списка модпаков: {str(e)}")
    
    def create_modpack_dialog(self):
        self.modpacks_tab.create_modpack_dialog()
    
    def create_modpack(self, name, description="", minecraft_version=None, modloader=None):
        try:
            modpack_path = os.path.join(self.MODPACKS_DIR, name)
            os.makedirs(modpack_path, exist_ok=True)
            
            os.makedirs(os.path.join(modpack_path, "mods"), exist_ok=True)
            os.makedirs(os.path.join(modpack_path, "config"), exist_ok=True)
            os.makedirs(os.path.join(modpack_path, "resourcepacks"), exist_ok=True)
            os.makedirs(os.path.join(modpack_path, "shaderpacks"), exist_ok=True)
            
            if minecraft_version is None:
                minecraft_version = self.main_tab.version_var.get()
            if modloader is None:
                modloader = self.main_tab.modloader_var.get()
            
            info = {
                'name': name,
                'description': description,
                'created': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'minecraft_version': minecraft_version,
                'modloader': modloader,
                'modloader_version': self.main_tab.modloader_version_var.get()
            }
            
            with open(os.path.join(modpack_path, "modpack_info.json"), 'w', encoding='utf-8') as f:
                json.dump(info, f, ensure_ascii=False, indent=2)
            
            self.current_modpack = name
            self.mods_tab.current_modpack_label.config(text=f"Текущий модпак: {name}")
            
            self.main_tab.log(f"Создан модпак: {name}")
            self.refresh_modpacks_list()
            self.refresh_modpack_selector()
            self.update_modpack_info_display()
            self.refresh_mods_list()
            
            messagebox.showinfo("Успех", f"Модпак '{name}' успешно создан!")
            
        except Exception as e:
            self.main_tab.log(f"Ошибка при создании модпака: {str(e)}")
            messagebox.showerror("Ошибка", f"Не удалось создать модпак: {str(e)}")
    
    def export_modpack(self):
        self.modpacks_tab.export_modpack()
    
    def refresh_modpack_selector(self):
        try:
            if not os.path.exists(self.MODPACKS_DIR):
                os.makedirs(self.MODPACKS_DIR, exist_ok=True)
                return
            
            modpack_folders = [f for f in os.listdir(self.MODPACKS_DIR) 
                            if os.path.isdir(os.path.join(self.MODPACKS_DIR, f))]
            
            modpack_names = []
            for modpack in modpack_folders:
                info_file = os.path.join(self.MODPACKS_DIR, modpack, "modpack_info.json")
                if os.path.exists(info_file):
                    try:
                        with open(info_file, 'r', encoding='utf-8') as f:
                            info = json.load(f)
                        modpack_names.append(info.get('name', modpack))
                    except Exception:
                        modpack_names.append(modpack)
                else:
                    modpack_names.append(modpack)
            
            if hasattr(self, 'modpack_selector'):
                self.modpack_selector['values'] = modpack_names
            
            self.main_tab.log(f"Загружено {len(modpack_names)} модпаков")
            
        except Exception as e:
            self.main_tab.log(f"Ошибка при обновлении селектора модпаков: {str(e)}")
    
    def on_modpack_selected_in_main_tab(self, event=None):
        try:
            selected_name = self.modpack_selector_var.get()
            if not selected_name:
                return
            
            for modpack in os.listdir(self.MODPACKS_DIR):
                if not os.path.isdir(os.path.join(self.MODPACKS_DIR, modpack)):
                    continue
                    
                info_file = os.path.join(self.MODPACKS_DIR, modpack, "modpack_info.json")
                if os.path.exists(info_file):
                    try:
                        with open(info_file, 'r', encoding='utf-8') as f:
                            info = json.load(f)
                        if info.get('name', modpack) == selected_name:
                            self.current_modpack = modpack
                            self.update_modpack_info()
                            break
                    except Exception as e:
                        self.main_tab.log(f"Ошибка при чтении модпака {modpack}: {str(e)}")
            
        except Exception as e:
            self.main_tab.log(f"Ошибка при выборе модпака: {str(e)}")
    
    def update_modpack_info(self):
        if not self.current_modpack:
            return
            
        info_file = os.path.join(self.MODPACKS_DIR, self.current_modpack, "modpack_info.json")
        if not os.path.exists(info_file):
            return
            
        try:
            with open(info_file, 'r', encoding='utf-8') as f:
                info = json.load(f)
            
            modpack_name = info.get('name', self.current_modpack)
            minecraft_version = info.get('minecraft_version', 'Не указана')
            modloader = info.get('modloader', 'Не указан')
            
            mods_dir = os.path.join(self.MODPACKS_DIR, self.current_modpack, "mods")
            mod_count = 0
            if os.path.exists(mods_dir):
                mod_count = len([f for f in os.listdir(mods_dir) if f.endswith('.jar')])
            
            info_text = f"{modpack_name} | Minecraft: {minecraft_version} | Модлоадер: {modloader} | Моды: {mod_count}"
            
            if hasattr(self, 'modpack_info_label'):
                self.modpack_info_label.config(text=info_text)
            
            if hasattr(self, 'modpack_selector_var'):
                self.modpack_selector_var.set(modpack_name)
            
            if minecraft_version and minecraft_version != 'Не указана':
                if minecraft_version in self.main_tab.version_combobox['values']:
                    self.main_tab.version_var.set(minecraft_version)
                    self.main_tab.on_minecraft_version_changed()
            
            if modloader and modloader != 'Не указан':
                if modloader in ["Vanilla", "Forge", "NeoForge", "Fabric", "Quilt"]:
                    self.main_tab.modloader_var.set(modloader)
                    self.main_tab.on_modloader_changed()
            
            if hasattr(self, 'mods_tab') and hasattr(self.mods_tab, 'current_modpack_label'):
                self.mods_tab.current_modpack_label.config(text=f"Текущий модпак: {modpack_name}")
            self.refresh_mods_list()
            
            self.main_tab.set_status(f"Модпак '{modpack_name}' загружен")
            
        except Exception as e:
            self.main_tab.log(f"Ошибка при обновлении информации о модпаке: {str(e)}")
    
    def update_modpack_info_display(self):
        if self.current_modpack:
            self.update_modpack_info()
        else:
            if hasattr(self, 'modpack_selector_var'):
                self.modpack_selector_var.set("")
            if hasattr(self, 'modpack_info_label'):
                self.modpack_info_label.config(text="Модпак не выбран")
    
    def quick_launch_modpack(self):
        try:
            if not hasattr(self, 'modpack_selector_var'):
                return
                
            selected_name = self.modpack_selector_var.get()
            if not selected_name:
                messagebox.showwarning("Внимание", "Выберите модпак для запуска")
                return
            
            if not self.current_modpack:
                messagebox.showwarning("Внимание", "Сначала выберите модпак из списка")
                return
            
            info_file = os.path.join(self.MODPACKS_DIR, self.current_modpack, "modpack_info.json")
            if not os.path.exists(info_file):
                messagebox.showwarning("Внимание", "Файл информации о модпаке не найден")
                return
            
            with open(info_file, 'r', encoding='utf-8') as f:
                info = json.load(f)
            
            minecraft_version = info.get('minecraft_version')
            modloader = info.get('modloader')
            
            if not minecraft_version or minecraft_version == 'Не указана':
                messagebox.showwarning("Внимание", "В модпаке не указана версия Minecraft")
                return
            
            if not self.check_and_install_prerequisites(minecraft_version, modloader):
                return
            
            self.main_tab.log(f"Запуск модпака {selected_name}...")
            self.version_manager.launch_minecraft()
            
        except Exception as e:
            self.main_tab.log(f"Ошибка при быстром запуске модпака: {str(e)}")
            messagebox.showerror("Ошибка", f"Не удалось запустить модпак: {str(e)}")
    
    def check_and_install_prerequisites(self, minecraft_version, modloader):
        if not self.version_manager.is_version_installed(minecraft_version, "Vanilla"):
            self.main_tab.log(f"Версия {minecraft_version} не установлена. Начинаем установку...")
            if not messagebox.askyesno("Установка", 
                                    f"Версия Minecraft {minecraft_version} не установлена.\n"
                                    f"Установить ее сейчас?"):
                return False
            
            self.main_tab.version_var.set(minecraft_version)
            self.main_tab.modloader_var.set("Vanilla")
            self.version_manager.install_version()
            self.main_tab.log("После установки нажмите 'Быстрый запуск' снова.")
            return False
        
        if modloader and modloader != "Vanilla" and modloader != 'Не указан':
            if not self.version_manager.is_version_installed(minecraft_version, modloader):
                self.main_tab.log(f"Модлоадер {modloader} не установлен. Начинаем установку...")
                if not messagebox.askyesno("Установка", 
                                        f"Модлоадер {modloader} не установлен.\n"
                                        f"Установить его сейчас?"):
                    return False
                
                self.main_tab.version_var.set(minecraft_version)
                self.main_tab.modloader_var.set(modloader)
                self.version_manager.install_version()
                self.main_tab.log("После установки нажмите 'Быстрый запуск' снова.")
                return False
        
        return True