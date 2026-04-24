from tabs import MainTab, ModsTab, ModpacksTab, SyncTab
from curseforge_handler import CurseForgeHandler
from version_manager import VersionManager
import minecraft_launcher_lib as mclib
from skin_manager import SkinManager
from tkinter import ttk, messagebox
from api_client import APIClient
from PIL import Image, ImageTk
from datetime import datetime
import tkinter as tk
import threading
import requests
import hashlib
import shutil
import json
import os

class MinecraftLauncher:
    def __init__(self, root):
        window_width = 800
        window_height = 560
        screen_width = 1920
        screen_height = 1080

        x = (screen_width // 2) - (window_width // 2)
        y = (screen_height // 2) - (window_height // 2)

        self.root = root
        self.root.title("Minecraft Launcher 1.0.1")
        self.root.geometry(f'{window_width}x{window_height}+{x}+{y}')
        self.root.configure(bg='#2b2b2b')

        # Основные директории
        self.MINECRAFT_DIR = ".minecraft"
        self.MODPACKS_DIR = os.path.join(self.MINECRAFT_DIR, "modpacks")
        self.MODS_CACHE_DIR = os.path.join(self.MINECRAFT_DIR, "mods_cache")
        self.SYNC_DIR = os.path.join(self.MINECRAFT_DIR, "sync")
        self.SKINS_SYNC_DIR = os.path.join(self.SYNC_DIR, "skins")
        self.MODS_SYNC_DIR = os.path.join(self.SYNC_DIR, "mods")
        
        # Создание всех необходимых директорий
        for directory in [self.MODPACKS_DIR, self.MODS_CACHE_DIR, 
                         self.SKINS_SYNC_DIR, self.MODS_SYNC_DIR]:
            os.makedirs(directory, exist_ok=True)
        
        self.current_modpack = None
        # Инициализация компонентов
        self.curseforge_handler = CurseForgeHandler(self)
        self.api_client = APIClient(self)
        self.version_manager = VersionManager(self)
        self.skin_manager = SkinManager(self)
        
        # Настройка интерфейса
        self.setup_notebook()
        
        # Обновление данных
        self.version_manager.refresh_versions()
        self.refresh_modpacks_list()
        
        # Автоматическая синхронизация
        self.root.after(1000, self.auto_sync_on_startup)
    
    def log(self, message):
        """Унифицированное логирование"""
        try:
            if hasattr(self, 'main_tab') and self.main_tab is not None:
                self.main_tab.log(message)
            else:
                print(f"[Launcher] {message}")
        except Exception:
            print(f"[Launcher] {message}")
    
    def auto_sync_on_startup(self):
        """Автоматическая синхронизация при запуске"""
        try:
            if self.api_client.test_connection():
                self.log("Сервер синхронизации доступен")
                threading.Thread(target=self.sync_all_data, daemon=True).start()
                self.skin_manager.prepare_local_skins_for_csl()
            else:
                self.log("Сервер недоступен, работаем офлайн")
                self.skin_manager.prepare_local_skins_for_csl()
        except Exception as e:
            self.log(f"Ошибка при запуске синхронизации: {str(e)}")

    def sync_all_data(self):
        """Фоновая синхронизация всех данных"""
        try:
            self.log("Начинаем синхронизацию с сервером...")
            self.sync_skins()
            self.sync_modpacks()
            self.log("Синхронизация завершена")
        except Exception as e:
            self.log(f"Ошибка синхронизации: {str(e)}")
    
    def sync_skins(self):
        """Синхронизация скинов с сервером"""
        try:
            manifest = self.api_client.get_skins_manifest()
            if not manifest:
                self.log("Не удалось получить манифест скинов")
                return False
            
            skins = manifest.get('skins', {})
            if not skins:
                self.log("На сервере нет скинов для синхронизации")
                return False
            
            downloaded_count = 0
            for username, skin_info in skins.items():
                skin_path = os.path.join(self.SKINS_SYNC_DIR, f"{username}.png")
                
                if os.path.exists(skin_path):
                    with open(skin_path, 'rb') as f:
                        local_hash = hashlib.md5(f.read()).hexdigest()
                    
                    if local_hash == skin_info.get('hash'):
                        continue
                
                if self.api_client.download_skin(username, skin_path):
                    downloaded_count += 1
            
            self.log(f"Синхронизация скинов завершена. Загружено: {downloaded_count}")
            self.skin_manager.prepare_local_skins_for_csl()
            
            return True
            
        except Exception as e:
            self.log(f"Ошибка синхронизации скинов: {str(e)}")
            return False
    
    def sync_modpacks(self):
        """Синхронизация модпаков с сервером"""
        try:
            modpacks = self.api_client.get_modpacks_list()
            if not modpacks:
                self.log("На сервере нет модпаков для синхронизации")
                return
            
            for modpack in modpacks:
                modpack_id = modpack.get('id')
                modpack_name = modpack.get('name')
                
                local_path = os.path.join(self.MODPACKS_DIR, modpack_name)
                if not os.path.exists(local_path):
                    self.log(f"Скачиваем модпак: {modpack_name}")
                    self.api_client.download_modpack(modpack_id, self.MODPACKS_DIR)
            
            self.refresh_modpacks_list()
            
        except Exception as e:
            self.log(f"Ошибка синхронизации модпаков: {str(e)}")
    
    def upload_current_skin(self):
        """Загрузить текущий скин на сервер"""
        username = self.main_tab.username_entry.get().strip()
        if not username:
            messagebox.showwarning("Внимание", "Введите имя пользователя")
            return
        
        skin_path = os.path.join(self.SKINS_SYNC_DIR, f"{username}.png")
        if not os.path.exists(skin_path):
            skin_path = os.path.join(self.MINECRAFT_DIR, "skins", f"{username}.png")
        
        if os.path.exists(skin_path):
            if self.api_client.upload_skin(skin_path, username):
                messagebox.showinfo("Успех", "Скин загружен на сервер")
            else:
                messagebox.showerror("Ошибка", "Не удалось загрузить скин")
        else:
            messagebox.showwarning("Внимание", "Локальный скин не найден")

    def setup_notebook(self):
        """Настройка вкладок"""
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=10)
        
        self.main_tab = MainTab(self.notebook, self)
        self.mods_tab = ModsTab(self.notebook, self)
        self.modpacks_tab = ModpacksTab(self.notebook, self)
        self.sync_tab = SyncTab(self.notebook, self)
        
        self.notebook.add(self.main_tab.frame, text="Основная")
        self.notebook.add(self.mods_tab.frame, text="Моды")
        self.notebook.add(self.modpacks_tab.frame, text="Модпаки")
        self.notebook.add(self.sync_tab.frame, text="Синхронизация")
    
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
        """Обновление списка модпаков"""
        try:
            self.modpacks_tab.refresh_modpacks_list()
            self.refresh_modpack_selector()
        except Exception as e:
            self.log(f"Ошибка при обновлении списка модпаков: {str(e)}")
    
    def create_modpack_dialog(self):
        self.modpacks_tab.create_modpack_dialog()
    
    def create_modpack(self, name, description="", minecraft_version=None, modloader=None):
        """Создание нового модпака"""
        try:
            modpack_path = os.path.join(self.MODPACKS_DIR, name)
            os.makedirs(modpack_path, exist_ok=True)
            
            for subdir in ["mods", "config", "resourcepacks", "shaderpacks"]:
                os.makedirs(os.path.join(modpack_path, subdir), exist_ok=True)
            
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
            
            info_file = os.path.join(modpack_path, "modpack_info.json")
            with open(info_file, 'w', encoding='utf-8') as f:
                json.dump(info, f, ensure_ascii=False, indent=2)
            
            self.current_modpack = name
            
            self.log(f"Создан модпак: {name}")
            self.refresh_modpacks_list()
            self.refresh_modpack_selector()
            
            messagebox.showinfo("Успех", f"Модпак '{name}' успешно создан!")
            
        except Exception as e:
            self.log(f"Ошибка при создании модпака: {str(e)}")
            messagebox.showerror("Ошибка", f"Не удалось создать модпак: {str(e)}")
    
    def export_modpack(self):
        self.modpacks_tab.export_modpack()
    
    def refresh_modpack_selector(self):
        """Обновление выпадающего списка модпаков"""
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
            
        except Exception as e:
            self.log(f"Ошибка при обновлении селектора модпаков: {str(e)}")
    
    def on_modpack_selected_in_main_tab(self, event=None):
        """Обработка выбора модпака в основной вкладке"""
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
                        self.log(f"Ошибка при чтении модпака: {str(e)}")
            
        except Exception as e:
            self.log(f"Ошибка при выборе модпака: {str(e)}")
    
    def update_modpack_info(self):
        """Обновление информации о выбранном модпаке"""
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
            
            if modloader and modloader != 'Не указан':
                if modloader in ["Vanilla", "Forge", "NeoForge", "Fabric", "Quilt"]:
                    self.main_tab.modloader_var.set(modloader)
            
            if hasattr(self, 'mods_tab') and hasattr(self.mods_tab, 'current_modpack_label'):
                self.mods_tab.current_modpack_label.config(text=f"Текущий модпак: {modpack_name}")
            self.refresh_mods_list()
            
        except Exception as e:
            self.log(f"Ошибка при обновлении информации о модпаке: {str(e)}")
    
    def quick_launch_modpack(self):
        """Быстрый запуск выбранного модпака"""
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
            
            self.log(f"Запуск модпака {selected_name}...")
            self.version_manager.launch_minecraft()
            
        except Exception as e:
            self.log(f"Ошибка при быстром запуске модпака: {str(e)}")
            messagebox.showerror("Ошибка", f"Не удалось запустить модпак: {str(e)}")
    
    def check_and_install_prerequisites(self, minecraft_version, modloader):
        """Проверка и установка необходимых компонентов"""
        if not self.version_manager.is_version_installed(minecraft_version, "Vanilla"):
            if not messagebox.askyesno("Установка", 
                                    f"Версия Minecraft {minecraft_version} не установлена.\n"
                                    f"Установить ее сейчас?"):
                return False
            
            self.main_tab.version_var.set(minecraft_version)
            self.main_tab.modloader_var.set("Vanilla")
            self.version_manager.install_version()
            return False
        
        if modloader and modloader != "Vanilla" and modloader != 'Не указан':
            if not self.version_manager.is_version_installed(minecraft_version, modloader):
                if not messagebox.askyesno("Установка", 
                                        f"Модлоадер {modloader} не установлен.\n"
                                        f"Установить его сейчас?"):
                    return False
                
                self.main_tab.version_var.set(minecraft_version)
                self.main_tab.modloader_var.set(modloader)
                self.version_manager.install_version()
                return False
        
        return True
    
    # Делегируем методы SkinManager
    def prepare_local_skins_for_csl(self):
        return self.skin_manager.prepare_local_skins_for_csl()
    
    def test_csl_local_config(self):
        return self.skin_manager.test_csl_local_config()
    
    def setup_skin_loader(self, minecraft_version, modloader):
        return self.skin_manager.setup_custom_skin_loader()
    
    def sync_skins_for_local_use(self):
        return self.skin_manager.sync_skins_for_local_use()
    
    def recreate_csl_config(self):
        """Пересоздание конфига CSL"""
        try:
            self.log("🔄 Пересоздаю конфиг CSL...")
            self.skin_manager.setup_custom_skin_loader()
            self.log("✅ Конфиг CSL пересоздан")
            
            # Показываем содержимое папки скинов
            skins_dir = os.path.join(self.MINECRAFT_DIR, "skins")
            if os.path.exists(skins_dir):
                files = os.listdir(skins_dir)
                self.log(f"📁 Файлов в папке skins: {len(files)}")
        except Exception as e:
            self.log(f"❌ Ошибка пересоздания конфига CSL: {str(e)}")