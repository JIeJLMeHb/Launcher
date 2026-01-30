from tabs import MainTab, ModsTab, ModpacksTab, SyncTab
from version_manager import VersionManager
from api_client import APIClient
import minecraft_launcher_lib as mclib
from tkinter import ttk, messagebox
from utils import InsecureSession
from PIL import Image, ImageTk
from datetime import datetime
import tkinter as tk
import subprocess
import threading
import tempfile
import shutil
import json
import os

class MinecraftLauncher:
    def __init__(self, root):

        window_width = 800
        window_height = 560
        """Центрирует окно на экране."""
        screen_width = 1920
        screen_height = 1080

        x = (screen_width // 2) - (window_width // 2)
        y = (screen_height // 2) - (window_height // 2)

        self.root = root
        self.root.title("Minecraft Launcher")
        self.root.geometry(f'{window_width}x{window_height}+{x}+{y}')
        self.root.configure(bg='#2b2b2b')

        image_path = os.path.join(os.path.dirname(__file__), 'logo.jpg')

        icon_image_pil = Image.open(image_path)
        icon_photo = ImageTk.PhotoImage(icon_image_pil)
        self.root.iconphoto(False, icon_photo)
        
        self.MINECRAFT_DIR = ".minecraft"
        self.MODPACKS_DIR = os.path.join(self.MINECRAFT_DIR, "modpacks")
        self.MODS_CACHE_DIR = os.path.join(self.MINECRAFT_DIR, "mods_cache")
        
        os.makedirs(self.MODPACKS_DIR, exist_ok=True)
        os.makedirs(self.MODS_CACHE_DIR, exist_ok=True)
        
        self.current_modpack = None
        
        # 1. Сначала создаем api_client
        from api_client import APIClient
        self.api_client = APIClient(self)
        
        # 2. Папки для синхронизации
        self.SYNC_DIR = os.path.join(self.MINECRAFT_DIR, "sync")
        self.SKINS_SYNC_DIR = os.path.join(self.SYNC_DIR, "skins")
        self.MODS_SYNC_DIR = os.path.join(self.SYNC_DIR, "mods")
        
        os.makedirs(self.SKINS_SYNC_DIR, exist_ok=True)
        os.makedirs(self.MODS_SYNC_DIR, exist_ok=True)
        
        # 3. Потом version_manager
        self.version_manager = VersionManager(self)
        
        # 4. Теперь можно настраивать интерфейс
        self.setup_notebook()
        
        # 5. Обновление данных
        self.version_manager.refresh_versions()
        self.refresh_modpacks_list()
        
        # 6. Автоматическая синхронизация (асинхронно, после создания UI)
        self.root.after(1000, self.auto_sync_on_startup)
    
        from api_client import APIClient
        self.api_client = APIClient(self)
        
        # Папки для синхронизации
        self.SYNC_DIR = os.path.join(self.MINECRAFT_DIR, "sync")
        self.SKINS_SYNC_DIR = os.path.join(self.SYNC_DIR, "skins")
        self.MODS_SYNC_DIR = os.path.join(self.SYNC_DIR, "mods")
        
        os.makedirs(self.SKINS_SYNC_DIR, exist_ok=True)
        os.makedirs(self.MODS_SYNC_DIR, exist_ok=True)
        
        # Автоматическая синхронизация при запуске
        self.root.after(1000, self.auto_sync_on_startup)
    
    def auto_sync_on_startup(self):
        try:
            if self.api_client.test_connection():
                self.main_tab.log("Сервер синхронизации доступен")
                threading.Thread(target=self.sync_all_data, daemon=True).start()
            else:
                self.main_tab.log("Сервер недоступен, работаем офлайн")
        except AttributeError as e:
            self.main_tab.log(f"Ошибка API клиента: {str(e)}")
        except Exception as e:
            self.main_tab.log(f"Ошибка синхронизации: {str(e)}")
    
    def sync_all_data(self):
        """Фоновая синхронизация всех данных"""
        try:
            self.main_tab.log("Начинаем синхронизацию с сервером...")
            
            # Синхронизируем скины
            self.sync_skins()
            
            # Синхронизируем модпаки
            self.sync_modpacks()
            
            self.main_tab.log("Синхронизация завершена")
            
        except Exception as e:
            self.main_tab.log(f"Ошибка синхронизации: {str(e)}")
    
    def sync_skins(self):
        """Синхронизация скинов с сервером"""
        try:
            manifest = self.api_client.get_skins_manifest()
            if not manifest:
                return
            
            # Скачиваем скины для всех пользователей из манифеста
            for username, skin_info in manifest.get('skins', {}).items():
                skin_path = os.path.join(self.SKINS_SYNC_DIR, f"{username}.png")
                
                # Проверяем, нужно ли обновлять
                if os.path.exists(skin_path):
                    with open(skin_path, 'rb') as f:
                        local_hash = hashlib.md5(f.read()).hexdigest()
                    
                    if local_hash == skin_info.get('hash'):
                        continue  # Скин актуален
                
                # Скачиваем новый скин
                self.api_client.download_skin(username, skin_path)
            
            self.main_tab.log(f"Синхронизировано {len(manifest.get('skins', {}))} скинов")
            
        except Exception as e:
            self.main_tab.log(f"Ошибка синхронизации скинов: {str(e)}")
    
    def sync_modpacks(self):
        """Синхронизация модпаков с сервером"""
        try:
            modpacks = self.api_client.get_modpacks_list()
            if not modpacks:
                return
            
            for modpack in modpacks:
                modpack_id = modpack.get('id')
                modpack_name = modpack.get('name')
                
                # Проверяем, есть ли локально
                local_path = os.path.join(self.MODPACKS_DIR, modpack_name)
                if not os.path.exists(local_path):
                    self.main_tab.log(f"Скачиваем модпак: {modpack_name}")
                    self.api_client.download_modpack(modpack_id, self.MODPACKS_DIR)
            
            self.refresh_modpacks_list()
            
        except Exception as e:
            self.main_tab.log(f"Ошибка синхронизации модпаков: {str(e)}")
    
    def upload_current_skin(self):
        """Загрузить текущий скин на сервер"""
        username = self.main_tab.username_entry.get().strip()
        if not username:
            messagebox.showwarning("Внимание", "Введите имя пользователя")
            return
        
        # Ищем локальный скин
        skin_path = os.path.join(self.SKINS_SYNC_DIR, f"{username}.png")
        if not os.path.exists(skin_path):
            # Проверяем в папке игры
            skin_path = os.path.join(self.MINECRAFT_DIR, "skins", f"{username}.png")
        
        if os.path.exists(skin_path):
            if self.api_client.upload_skin(username, skin_path):
                messagebox.showinfo("Успех", "Скин загружен на сервер")
            else:
                messagebox.showerror("Ошибка", "Не удалось загрузить скин")
        else:
            messagebox.showwarning("Внимание", "Локальный скин не найден")


    def setup_notebook(self):
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
    def create_instructions_file(self):
        """Создает файл с инструкциями для пользователей"""
        instructions_path = "README_СКИНЫ.txt"
        if not os.path.exists(instructions_path):
            instructions = """ИНСТРУКЦИЯ ПО ЗАГРУЗКЕ СКИНОВ

    1. Покажите эту инструкцию друзьям
    2. Убедитесь, что они заменили URL в api_config.json
    3. Попросите их зарегистрироваться через вкладку "Синхронизация"
    4. Затем они смогут загружать скины через ту же вкладку

    Ваш URL сервера: {self.api_client.base_url}
    """
            with open(instructions_path, 'w', encoding='utf-8') as f:
                f.write(instructions)
            self.main_tab.log(f"Создана инструкция: {instructions_path}")

            
    def setup_skin_loader(self, minecraft_version, modloader):
        """Автоматически настраивает Custom Skin Loader"""
        try:
            config_dir = os.path.join(self.MINECRAFT_DIR, "CustomSkinLoader")
            os.makedirs(config_dir, exist_ok=True)
            
            config_path = os.path.join(config_dir, "CustomSkinLoader.json")
            
            # Используем CustomSkinAPI вместо Legacy
            config = {
                "enable": True,
                "loadlist": [
                    {
                        "name": "MySkinAPI",
                        "type": "CustomSkinAPI",
                        # CustomSkinAPI будет делать запрос к этому URL + username
                        "root": f"{self.api_client.base_url}/api/csl/"
                    }
                ],
                "forceLoadAllTextures": False,
                "enableDynamicSkull": True,
                "enableTransparentSkin": True,
                "ignoreHttpsCertificate": False,
                "enableLog": True,
                "cacheExpiry": 30,
                "updateInterval": 7
            }
            
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            
            self.main_tab.log(f"✅ Конфиг CSL (CustomSkinAPI) создан: {config_path}")
            
            return True
            
        except Exception as e:
            self.main_tab.log(f"❌ Ошибка настройки Skin Loader: {str(e)}")
            return False

    def test_skin_urls(self):
        """Тестирует все возможные URL для скинов"""
        try:
            username = self.main_tab.username_entry.get().strip()
            if not username:
                return
            
            self.main_tab.log("🔍 Тестируем URL скинов...")
            
            test_urls = [
                (f"{self.api_client.base_url}/api/skins/{username}", "API без расширения"),
                (f"{self.api_client.base_url}/uploads/skins/{username}", "Статика без расширения"),
                (f"{self.api_client.base_url}/uploads/skins/{username}.png", "Статика с расширением"),
            ]
            
            for url, description in test_urls:
                try:
                    # Пробуем HEAD запрос
                    response = requests.head(url, timeout=5, allow_redirects=True)
                    self.main_tab.log(f"  {description}: HEAD -> {response.status_code}")
                    
                    # Пробуем GET запрос (только если HEAD вернул 200)
                    if response.status_code == 200:
                        response_get = requests.get(url, timeout=5, stream=True)
                        self.main_tab.log(f"    GET -> {response_get.status_code}, "
                                        f"Content-Type: {response_get.headers.get('Content-Type', 'N/A')}, "
                                        f"Size: {response_get.headers.get('Content-Length', 'N/A')} байт")
                        
                        # Сохраняем тестовый файл для проверки
                        if response_get.status_code == 200:
                            test_dir = os.path.join(self.MINECRAFT_DIR, "test_skins")
                            os.makedirs(test_dir, exist_ok=True)
                            test_file = os.path.join(test_dir, f"{description.replace(' ', '_')}.png")
                            
                            with open(test_file, 'wb') as f:
                                for chunk in response_get.iter_content(chunk_size=8192):
                                    f.write(chunk)
                            
                            file_size = os.path.getsize(test_file)
                            self.main_tab.log(f"    📁 Сохранен в: {test_file} ({file_size} байт)")
                            
                except Exception as e:
                    self.main_tab.log(f"  ❌ {description}: Ошибка - {str(e)}")
        
        except Exception as e:
            self.main_tab.log(f"❌ Ошибка тестирования URL: {str(e)}")

    def download_custom_skin_loader(self):
        """Скачивает Custom Skin Loader автоматически"""
        try:
            self.main_tab.log("⬇️  Скачиваю Custom Skin Loader...")
            
            # URL последней версии с Modrinth
            csl_url = "https://cdn.modrinth.com/data/P5qVSOG1/versions/14.27/CustomSkinLoader_14.27_Forge.jar"
            
            mods_dir = os.path.join(self.MINECRAFT_DIR, "mods")
            os.makedirs(mods_dir, exist_ok=True)
            
            response = requests.get(csl_url, timeout=30)
            if response.status_code == 200:
                file_path = os.path.join(mods_dir, "CustomSkinLoader_14.27_Forge.jar")
                with open(file_path, 'wb') as f:
                    f.write(response.content)
                
                self.main_tab.log(f"✅ Custom Skin Loader скачан: {file_path}")
                return True
            else:
                self.main_tab.log(f"❌ Не удалось скачать CSL: {response.status_code}")
                return False
                
        except Exception as e:
            self.main_tab.log(f"❌ Ошибка скачивания CSL: {str(e)}")
            return False

    def test_csl_config(self):
        """Тестирует конфигурацию Custom Skin Loader"""
        try:
            username = self.main_tab.username_entry.get().strip()
            if username:
                # Проверяем все возможные URL
                test_urls = [
                    f"{self.api_client.base_url}/api/skins/{username}",
                    f"{self.api_client.base_url}/api/skins/{username}/skin",
                    f"{self.api_client.base_url}/uploads/skins/{username}.png",
                    f"{self.api_client.base_url}/api/skins/{username}/textures"
                ]
                
                for url in test_urls:
                    response = requests.head(url, timeout=5)
                    self.main_tab.log(f"🔗 {url} -> {response.status_code}")
                    
                    if response.status_code == 200:
                        self.main_tab.log(f"✅ URL работает: {url}")
                        
        except Exception as e:
            self.main_tab.log(f"⚠️ Ошибка тестирования: {str(e)}")

    def sync_skins_for_local_use(self):
        """Создает локальные копии скинов для Custom Skin Loader"""
        try:
            skins_dir = os.path.join(self.MINECRAFT_DIR, "skins")
            os.makedirs(skins_dir, exist_ok=True)
            
            # Копируем скины из sync/skins в .minecraft/skins
            for skin_file in os.listdir(self.SKINS_SYNC_DIR):
                if skin_file.endswith('.png'):
                    src = os.path.join(self.SKINS_SYNC_DIR, skin_file)
                    dst = os.path.join(skins_dir, skin_file)
                    shutil.copy2(src, dst)
            
            self.main_tab.log(f"✅ Локальные скины подготовлены: {skins_dir}")
            
        except Exception as e:
            self.main_tab.log(f"⚠️ Ошибка подготовки локальных скинов: {str(e)}")

    def sync_skins(self):
        """Синхронизация скинов с сервером"""
        try:
            manifest = self.api_client.get_skins_manifest()
            if not manifest:
                self.main_tab.log("Не удалось получить манифест скинов")
                return
            
            skins = manifest.get('skins', {})
            self.main_tab.log(f"Начало синхронизации {len(skins)} скинов")
            
            for username, skin_info in skins.items():
                skin_path = os.path.join(self.SKINS_SYNC_DIR, f"{username}.png")
                
                # Проверяем, нужно ли обновлять
                if os.path.exists(skin_path):
                    import hashlib
                    with open(skin_path, 'rb') as f:
                        local_hash = hashlib.md5(f.read()).hexdigest()
                    
                    if local_hash == skin_info.get('hash'):
                        continue  # Скин актуален
                
                # Скачиваем новый скин
                if self.api_client.download_skin(username, skin_path):
                    self.main_tab.log(f"Скин для {username} обновлен")
                else:
                    self.main_tab.log(f"Не удалось скачать скин для {username}")
            
            self.main_tab.log(f"Синхронизация скинов завершена")
            
        except Exception as e:
            self.main_tab.log(f"Ошибка синхронизации скинов: {str(e)}")
    def prepare_local_skins_for_csl(self):
        """Подготавливает локальные скины для Custom Skin Loader"""
        try:
            sync_dir = self.SKINS_SYNC_DIR
            csl_dir = os.path.join(self.MINECRAFT_DIR, "skins_csl")
            os.makedirs(csl_dir, exist_ok=True)
            
            # Копируем и переименовываем файлы для CSL
            for skin_file in os.listdir(sync_dir):
                if skin_file.endswith('.png'):
                    src = os.path.join(sync_dir, skin_file)
                    username = os.path.splitext(skin_file)[0]
                    
                    # Создаем несколько вариантов для CSL
                    dst1 = os.path.join(csl_dir, username)  # Без расширения
                    dst2 = os.path.join(csl_dir, f"{username}.png")  # С расширением
                    
                    shutil.copy2(src, dst1)
                    shutil.copy2(src, dst2)
            
            self.main_tab.log(f"✅ Локальные скины подготовлены для CSL: {csl_dir}")
            
            # Обновляем конфиг CSL
            self.update_csl_config_with_local_dir(csl_dir)
            
        except Exception as e:
            self.main_tab.log(f"⚠️ Ошибка подготовки локальных скинов: {str(e)}")

    def update_csl_config_with_local_dir(self, csl_dir):
        """Обновляет конфиг CSL с локальной директорией"""
        try:
            config_dir = os.path.join(self.MINECRAFT_DIR, "CustomSkinLoader")
            config_path = os.path.join(config_dir, "CustomSkinLoader.json")
            
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                
                # Добавляем локальную директорию в loadlist
                csl_dir_formatted = os.path.abspath(csl_dir).replace("\\", "/") + "/"
                
                # Ищем и обновляем LocalSkins
                for i, loader in enumerate(config.get("loadlist", [])):
                    if loader.get("name") == "LocalSkins":
                        config["loadlist"][i]["root"] = csl_dir_formatted
                        break
                else:
                    # Если LocalSkins не найден, добавляем
                    config["loadlist"].insert(0, {
                        "name": "LocalSkinsCSL",
                        "type": "Legacy",
                        "root": csl_dir_formatted
                    })
                
                with open(config_path, 'w', encoding='utf-8') as f:
                    json.dump(config, f, indent=2, ensure_ascii=False)
                
                self.main_tab.log(f"✅ Конфиг CSL обновлен с локальной директорией")
                
        except Exception as e:
            self.main_tab.log(f"⚠️ Ошибка обновления конфига CSL: {str(e)}")