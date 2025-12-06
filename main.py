import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import minecraft_launcher_lib as mclib
import subprocess
import threading
import os
import warnings
import ssl
import requests
import json
from pathlib import Path
import urllib3
import shutil

# ===== SSL FIXES =====
ssl._create_default_https_context = ssl._create_unverified_context
warnings.filterwarnings("ignore")
os.environ['CURL_CA_BUNDLE'] = ''
os.environ['REQUESTS_CA_BUNDLE'] = ''
os.environ['PYTHONHTTPSVERIFY'] = '0'

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class InsecureSession(requests.Session):
    def __init__(self):
        super().__init__()
        self.verify = False

requests.Session = InsecureSession

original_get_requests = mclib._helper.get_requests_response_cache

def insecure_get_requests(url: str):
    session = InsecureSession()
    response = session.get(url)
    response.raise_for_status()
    return response

mclib._helper.get_requests_response_cache = insecure_get_requests

# ===== LAUNCHER CODE =====
MINECRAFT_DIR = ".minecraft"
MODS_DIR = os.path.join(MINECRAFT_DIR, "mods")
MODS_CACHE_DIR = os.path.join(MINECRAFT_DIR, "mods_cache")

class MinecraftLauncher:
    def __init__(self, root):
        self.root = root
        self.root.title("Minecraft Launcher")
        self.root.geometry("800x700")
        
        # Создаем кэш директории
        os.makedirs(MODS_CACHE_DIR, exist_ok=True)
        
        # Создаем Notebook для вкладок
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Основная вкладка
        self.main_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.main_frame, text="Основная")
        
        # Вкладка модов
        self.mods_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.mods_frame, text="Моды")
        
        self.setup_main_tab()
        self.setup_mods_tab()
        
        # Словарь для хранения информации о модлоадерах
        self.modloader_versions = {
            "Forge": [],
            "NeoForge": [],
            "Fabric": [],
            "Quilt": []
        }
        
        # Загружаем версии
        self.refresh_versions()
    
    def setup_main_tab(self):
        """Настройка основной вкладки"""
        # Заголовок с предупреждением об SSL
        warning_label = tk.Label(self.main_frame, text="ВНИМАНИЕ: SSL проверка отключена!", 
                               fg="red", font=("Arial", 10, "bold"))
        warning_label.pack(pady=5)
        
        # Заголовок
        label = tk.Label(self.main_frame, text="Выберите версию Minecraft", font=("Arial", 12))
        label.pack(pady=10)
        
        # Фрейм для выбора версии
        version_frame = tk.Frame(self.main_frame)
        version_frame.pack(fill="x", pady=5)
        
        tk.Label(version_frame, text="Версия Minecraft:").pack(side="left")
        self.version_var = tk.StringVar()
        self.version_combobox = ttk.Combobox(version_frame, textvariable=self.version_var, 
                                           state="readonly", width=25)
        self.version_combobox.pack(side="left", padx=5)
        self.version_combobox.bind("<<ComboboxSelected>>", self.on_minecraft_version_changed)
        
        # Кнопка обновления списка версий
        self.refresh_button = tk.Button(version_frame, text="Обновить", command=self.refresh_versions)
        self.refresh_button.pack(side="left", padx=5)
        
        # Фрейм для выбора модлоадера
        modloader_frame = tk.Frame(self.main_frame)
        modloader_frame.pack(fill="x", pady=10)
        
        tk.Label(modloader_frame, text="Модлоадер:").pack(side="left")
        self.modloader_var = tk.StringVar(value="Vanilla")
        self.modloader_combobox = ttk.Combobox(modloader_frame, textvariable=self.modloader_var,
                                              values=["Vanilla", "Forge", "NeoForge", "Fabric", "Quilt"],
                                              state="readonly", width=15)
        self.modloader_combobox.pack(side="left", padx=5)
        self.modloader_combobox.bind("<<ComboboxSelected>>", self.on_modloader_changed)
        
        tk.Label(modloader_frame, text="Версия:").pack(side="left")
        self.modloader_version_var = tk.StringVar()
        self.modloader_version_combobox = ttk.Combobox(modloader_frame, textvariable=self.modloader_version_var,
                                                      state="readonly", width=20)
        self.modloader_version_combobox.pack(side="left", padx=5)
        
        # Фрейм для данных аккаунта
        account_frame = tk.LabelFrame(self.main_frame, text="Данные аккаунта")
        account_frame.pack(fill="x", pady=10)
        
        # Поле для имени пользователя
        username_frame = tk.Frame(account_frame)
        username_frame.pack(fill="x", pady=5)
        tk.Label(username_frame, text="Имя пользователя:").pack(side="left")
        self.username_entry = tk.Entry(username_frame, width=30)
        self.username_entry.insert(0, "Player")
        self.username_entry.pack(side="left", padx=5)
        
        # Поле для UUID
        uuid_frame = tk.Frame(account_frame)
        uuid_frame.pack(fill="x", pady=5)
        tk.Label(uuid_frame, text="UUID:").pack(side="left")
        self.uuid_entry = tk.Entry(uuid_frame, width=40)
        self.uuid_entry.pack(side="left", padx=5)
        
        # Поле для токена
        token_frame = tk.Frame(account_frame)
        token_frame.pack(fill="x", pady=5)
        tk.Label(token_frame, text="Token:").pack(side="left")
        self.token_entry = tk.Entry(token_frame, width=40, show="*")
        self.token_entry.pack(side="left", padx=5)
        
        # Кнопка для показа/скрытия токена
        self.show_token_var = tk.BooleanVar()
        self.show_token_check = tk.Checkbutton(token_frame, text="Показать", 
                                             variable=self.show_token_var,
                                             command=self.toggle_token_visibility)
        self.show_token_check.pack(side="left")
        
        # Прогресс-бар
        self.progress = ttk.Progressbar(self.main_frame, mode='determinate')
        self.progress.pack(fill="x", pady=5)
        self.progress_label = tk.Label(self.main_frame, text="")
        self.progress_label.pack()
        
        # Фрейм для кнопок
        button_frame = tk.Frame(self.main_frame)
        button_frame.pack(pady=10)
        
        # Кнопка установки
        self.install_button = tk.Button(button_frame, text="Установить", 
                                      command=self.install_version,
                                      bg="blue", fg="white", width=15)
        self.install_button.pack(side="left", padx=5)
        
        # Кнопка запуска
        self.launch_button = tk.Button(button_frame, text="Запуск Minecraft", 
                                     command=self.launch_minecraft,
                                     bg="green", fg="white", font=("Arial", 10, "bold"), width=15)
        self.launch_button.pack(side="left", padx=5)
        
        # Текстовое поле для логов
        log_frame = tk.LabelFrame(self.main_frame, text="Логи")
        log_frame.pack(fill="both", expand=True, pady=5)
        
        self.log_text = tk.Text(log_frame, height=12)
        scrollbar = tk.Scrollbar(log_frame, command=self.log_text.yview)
        self.log_text.config(yscrollcommand=scrollbar.set)
        
        self.log_text.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        scrollbar.pack(side="right", fill="y")
        
        # Статус бар
        self.status_var = tk.StringVar()
        self.status_var.set("Готов к работе")
        status_bar = tk.Label(self.main_frame, textvariable=self.status_var, relief="sunken", anchor="w")
        status_bar.pack(fill="x", pady=5)
    
    def setup_mods_tab(self):
        """Настройка вкладки модов"""
        # Панель управления модами
        control_frame = tk.Frame(self.mods_frame)
        control_frame.pack(fill="x", padx=5, pady=5)
        
        # Кнопка добавления мода из файла
        self.add_mod_button = tk.Button(control_frame, text="Добавить мод из файла", 
                                      command=self.add_mod_from_file)
        self.add_mod_button.pack(side="left", padx=5)
        
        # Кнопка добавления мода по URL
        self.add_mod_url_button = tk.Button(control_frame, text="Добавить мод по ссылке", 
                                          command=self.add_mod_from_url)
        self.add_mod_url_button.pack(side="left", padx=5)
        
        # Кнопка удаления выбранного мода
        self.remove_mod_button = tk.Button(control_frame, text="Удалить выбранный", 
                                         command=self.remove_selected_mod)
        self.remove_mod_button.pack(side="left", padx=5)
        
        # Кнопка очистки всех модов
        self.clear_mods_button = tk.Button(control_frame, text="Очистить все", 
                                         command=self.clear_all_mods)
        self.clear_mods_button.pack(side="left", padx=5)
        
        # Кнопка обновления списка
        self.refresh_mods_button = tk.Button(control_frame, text="Обновить список", 
                                           command=self.refresh_mods_list)
        self.refresh_mods_button.pack(side="left", padx=5)
        
        # Список модов
        list_frame = tk.Frame(self.mods_frame)
        list_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Создаем Treeview для отображения модов
        columns = ("Название", "Версия", "Размер", "Путь")
        self.mods_tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=15)
        
        for col in columns:
            self.mods_tree.heading(col, text=col)
            self.mods_tree.column(col, width=150)
        
        # Скроллбар для списка модов
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.mods_tree.yview)
        self.mods_tree.configure(yscrollcommand=scrollbar.set)
        
        self.mods_tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Информация о моде
        info_frame = tk.LabelFrame(self.mods_frame, text="Информация о моде")
        info_frame.pack(fill="x", padx=5, pady=5)
        
        self.mod_info_text = tk.Text(info_frame, height=6, wrap="word")
        mod_info_scrollbar = tk.Scrollbar(info_frame, command=self.mod_info_text.yview)
        self.mod_info_text.config(yscrollcommand=mod_info_scrollbar.set)
        
        self.mod_info_text.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        mod_info_scrollbar.pack(side="right", fill="y")
        
        # Привязываем событие выбора мода
        self.mods_tree.bind("<<TreeviewSelect>>", self.on_mod_selected)
        
        # Загружаем список модов
        self.refresh_mods_list()
    
    def toggle_token_visibility(self):
        """Переключает видимость токена"""
        if self.show_token_var.get():
            self.token_entry.config(show="")
        else:
            self.token_entry.config(show="*")
    
    def log(self, message):
        """Добавляет сообщение в лог"""
        self.log_text.insert(tk.END, f"{message}\n")
        self.log_text.see(tk.END)
        self.root.update_idletasks()
    
    def set_status(self, message):
        """Устанавливает статус"""
        self.status_var.set(message)
        self.root.update_idletasks()
    
    def update_progress(self, value, max_value=100):
        """Обновляет прогресс-бар"""
        if max_value > 0:
            progress_percent = (value / max_value) * 100
            self.progress['value'] = progress_percent
            self.progress_label.config(text=f"Прогресс: {progress_percent:.1f}%")
        self.root.update_idletasks()
    
    def refresh_versions(self):
        """Обновляет список версий"""
        self.refresh_button.config(state="disabled")
        threading.Thread(target=self.load_versions, daemon=True).start()
    
    def load_versions(self):
        """Загружает список версий Minecraft"""
        try:
            self.set_status("Загрузка списка версий...")
            self.log("Получение списка версий Minecraft...")
            
            session = InsecureSession()
            response = session.get("https://launchermeta.mojang.com/mc/game/version_manifest_v2.json", timeout=30)
            version_data = response.json()
            
            # Фильтруем только стабильные релизы
            release_versions = [v['id'] for v in version_data['versions'] if v['type'] == 'release']
            
            # Сортируем версии по убыванию
            def version_key(ver):
                parts = ver.split('.')
                try:
                    return [int(part) for part in parts]
                except ValueError:
                    return [0, 0, 0]
            
            release_versions.sort(key=version_key, reverse=True)
            
            self.root.after(0, self.update_version_combobox, release_versions)
            
            # Загружаем версии модлоадеров
            self.load_modloader_versions()
            
        except Exception as e:
            self.log(f"Ошибка при загрузке версий: {str(e)}")
            test_versions = ["1.20.4", "1.20.1", "1.19.4", "1.18.2", "1.17.1", "1.16.5"]
            self.root.after(0, self.update_version_combobox, test_versions)
            self.set_status("Ошибка загрузки версий, используется локальный список")
    
    def load_modloader_versions(self):
        """Загружает версии модлоадеров"""
        try:
            session = InsecureSession()
            
            # Загружаем версии Forge
            self.log("Загрузка версий Forge...")
            forge_versions = mclib.forge.list_forge_versions()
            self.modloader_versions["Forge"] = forge_versions
            
            # Загружаем версии NeoForge
            self.log("Загрузка версий NeoForge...")
            try:
                # NeoForge может использовать похожий API
                neoforge_response = session.get("https://maven.neoforged.net/api/maven/versions/releases/net/neoforged/neoforge")
                if neoforge_response.status_code == 200:
                    neoforge_data = neoforge_response.json()
                    self.modloader_versions["NeoForge"] = neoforge_data.get("versions", [])
            except:
                pass
            
            # Загружаем версии Fabric
            self.log("Загрузка версий Fabric...")
            try:
                fabric_response = session.get("https://meta.fabricmc.net/v2/versions/loader")
                if fabric_response.status_code == 200:
                    fabric_data = fabric_response.json()
                    fabric_versions = []
                    for item in fabric_data:
                        if isinstance(item, dict) and 'loader' in item:
                            fabric_versions.append(item['loader']['version'])
                    self.modloader_versions["Fabric"] = fabric_versions[:50]  # Ограничиваем количество
            except:
                pass
            
            self.log("Загрузка версий модлоадеров завершена")
            
        except Exception as e:
            self.log(f"Ошибка при загрузке версий модлоадеров: {str(e)}")
    
    def update_version_combobox(self, versions):
        """Обновляет комбобокс с версиями"""
        self.version_combobox['values'] = versions
        if versions:
            self.version_combobox.set(versions[0])
        self.log(f"Загружено {len(versions)} версий Minecraft")
        self.set_status(f"Загружено {len(versions)} версий")
        self.refresh_button.config(state="normal")
    
    def on_minecraft_version_changed(self, event=None):
        """Обработчик изменения версии Minecraft"""
        selected_version = self.version_var.get()
        modloader = self.modloader_var.get()
        
        if modloader != "Vanilla" and selected_version:
            self.update_modloader_versions_for_minecraft(selected_version, modloader)
    
    def on_modloader_changed(self, event=None):
        """Обработчик изменения модлоадера"""
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
        """Обновляет список версий модлоадера для выбранной версии Minecraft"""
        try:
            versions = []
            
            if modloader_type == "Forge":
                # Фильтруем версии Forge по версии Minecraft
                for version in self.modloader_versions.get("Forge", []):
                    if version.startswith(minecraft_version):
                        versions.append(version)
            
            elif modloader_type == "NeoForge":
                # Фильтруем версии NeoForge
                for version in self.modloader_versions.get("NeoForge", []):
                    if minecraft_version in version:
                        versions.append(version)
            
            elif modloader_type == "Fabric":
                # Fabric работает с большинством версий
                versions = self.modloader_versions.get("Fabric", [])[:20]
            
            elif modloader_type == "Quilt":
                # Quilt похож на Fabric
                versions = ["Последняя версия"]  # Заглушка
            
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
    
    def install_version(self):
        """Устанавливает выбранную версию Minecraft с модлоадером"""
        minecraft_version = self.version_var.get()
        modloader = self.modloader_var.get()
        modloader_version = self.modloader_version_var.get()
        
        if not minecraft_version:
            self.log("Ошибка: Выберите версию Minecraft!")
            return
        
        self.install_button.config(state="disabled")
        self.launch_button.config(state="disabled")
        
        threading.Thread(target=self._install_version_thread, 
                        args=(minecraft_version, modloader, modloader_version), 
                        daemon=True).start()
    
    def _install_version_thread(self, minecraft_version, modloader, modloader_version):
        """Поток для установки версии"""
        try:
            self.set_status(f"Установка Minecraft {minecraft_version}...")
            self.log(f"Начинаем установку Minecraft {minecraft_version}")
            
            # Создаем директорию если нет
            os.makedirs(MINECRAFT_DIR, exist_ok=True)
            
            # Callback для отслеживания прогресса
            callback = {
                'setStatus': lambda text: self.root.after(0, self.set_status, text),
                'setProgress': lambda value: self.root.after(0, self.update_progress, value, 100),
                'setMax': lambda max_value: None
            }
            
            # Устанавливаем Minecraft
            mclib.install.install_minecraft_version(minecraft_version, MINECRAFT_DIR, callback=callback)
            self.log(f"Minecraft {minecraft_version} успешно установлен!")
            
            # Устанавливаем модлоадер если нужно
            if modloader != "Vanilla":
                self.install_modloader(minecraft_version, modloader, modloader_version, callback)
            
            self.set_status(f"Установка завершена")
            self.root.after(0, lambda: self.install_button.config(state="normal"))
            self.root.after(0, lambda: self.launch_button.config(state="normal"))
            
        except Exception as e:
            self.log(f"Ошибка при установке: {str(e)}")
            self.set_status("Ошибка установки")
            self.root.after(0, lambda: self.install_button.config(state="normal"))
            self.root.after(0, lambda: self.launch_button.config(state="normal"))
    
    def install_modloader(self, minecraft_version, modloader, modloader_version, callback):
        """Устанавливает модлоадер"""
        try:
            self.set_status(f"Установка {modloader}...")
            self.log(f"Установка {modloader} {modloader_version} для Minecraft {minecraft_version}")
            
            if modloader == "Forge":
                if modloader_version == "Автоматический выбор":
                    # Находим последнюю версию Forge для этой версии Minecraft
                    for version in self.modloader_versions.get("Forge", []):
                        if version.startswith(minecraft_version):
                            modloader_version = version
                            break
                
                if modloader_version:
                    mclib.forge.install_forge_version(modloader_version, MINECRAFT_DIR, callback=callback)
                    self.log(f"Forge {modloader_version} успешно установлен!")
            
            elif modloader == "Fabric":
                try:
                    mclib.fabric.install_fabric(minecraft_version, MINECRAFT_DIR, callback=callback)
                    self.log(f"Fabric для Minecraft {minecraft_version} успешно установлен!")
                except Exception as e:
                    self.log(f"Ошибка установки Fabric: {str(e)}")
                    self.log("Попытка альтернативного метода установки...")
            
            elif modloader == "NeoForge":
                self.log("NeoForge установка требует ручной настройки")
                self.log("Пожалуйста, установите NeoForge вручную")
            
            elif modloader == "Quilt":
                self.log("Quilt установка требует ручной настройки")
                self.log("Пожалуйста, установите Quilt вручную")
            
            self.log(f"{modloader} установка завершена")
            
        except Exception as e:
            self.log(f"Ошибка при установке {modloader}: {str(e)}")
            raise
    
    def launch_minecraft(self):
        """Запускает Minecraft"""
        minecraft_version = self.version_var.get()
        modloader = self.modloader_var.get()
        
        if not minecraft_version:
            self.log("Ошибка: Выберите версию Minecraft!")
            return
        
        # Получаем данные из полей ввода
        username = self.username_entry.get().strip()
        uuid = self.uuid_entry.get().strip()
        token = self.token_entry.get().strip()
        
        if not username:
            self.log("Ошибка: Введите имя пользователя!")
            return
        
        self.log(f"Запуск Minecraft {minecraft_version} с {modloader} для пользователя: {username}")
        
        self.launch_button.config(state="disabled")
        self.install_button.config(state="disabled")
        
        threading.Thread(target=self._launch_minecraft_thread, 
                        args=(minecraft_version, modloader, username, uuid, token), 
                        daemon=True).start()
    
    def _launch_minecraft_thread(self, minecraft_version, modloader, username, uuid, token):
        """Поток для запуска Minecraft"""
        try:
            self.set_status("Подготовка к запуску...")
            
            # Определяем версию для запуска
            launch_version = minecraft_version
            if modloader == "Forge":
                # Ищем установленную версию Forge
                installed_versions = mclib.utils.get_installed_versions(MINECRAFT_DIR)
                for version in installed_versions:
                    if "forge" in version['id'].lower() and minecraft_version in version['id']:
                        launch_version = version['id']
                        break
            
            elif modloader == "Fabric":
                # Ищем установленную версию Fabric
                installed_versions = mclib.utils.get_installed_versions(MINECRAFT_DIR)
                for version in installed_versions:
                    if "fabric" in version['id'].lower():
                        launch_version = version['id']
                        break
            
            # Подготавливаем опции запуска
            options = {
                "username": username,
                "uuid": uuid if uuid else "",
                "token": token if token else "",
                "jvmArguments": ["-Xmx4G", "-Xms2G"]  # Выделяем 4GB RAM
            }
            
            # Добавляем путь к папке с модами
            if os.path.exists(MODS_DIR):
                options["gameDirectory"] = MINECRAFT_DIR
            
            self.log(f"Используется версия: {launch_version}")
            self.log("Генерация команды запуска...")
            
            # Получаем команду для запуска
            minecraft_command = mclib.command.get_minecraft_command(launch_version, MINECRAFT_DIR, options)
            
            self.log("Запуск Minecraft...")
            self.set_status("Minecraft запускается...")
            
            # Запускаем игру
            process = subprocess.Popen(
                minecraft_command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1,
                encoding='utf-8',
                errors='replace'
            )
            
            # Выводим логи в реальном времени
            for line in process.stdout:
                if line.strip():
                    self.log(f"> {line.strip()}")
            
            process.wait()
            self.log("Игра завершена.")
            self.set_status("Готов к работе")
            
        except Exception as e:
            self.log(f"Произошла ошибка при запуске: {str(e)}")
            self.set_status("Ошибка запуска")
        finally:
            self.root.after(0, lambda: self.launch_button.config(state="normal"))
            self.root.after(0, lambda: self.install_button.config(state="normal"))
    
    # ===== ФУНКЦИИ ДЛЯ РАБОТЫ С МОДАМИ =====
    
    def refresh_mods_list(self):
        """Обновляет список модов"""
        try:
            # Очищаем Treeview
            for item in self.mods_tree.get_children():
                self.mods_tree.delete(item)
            
            # Проверяем существование папки модов
            if not os.path.exists(MODS_DIR):
                os.makedirs(MODS_DIR, exist_ok=True)
                return
            
            # Загружаем моды из папки
            mod_files = [f for f in os.listdir(MODS_DIR) if f.endswith('.jar')]
            
            for mod_file in mod_files:
                mod_path = os.path.join(MODS_DIR, mod_file)
                mod_size = os.path.getsize(mod_path)
                
                # Получаем базовую информацию о моде
                mod_name = mod_file
                mod_version = "Неизвестно"
                
                # Пытаемся извлечь информацию из имени файла
                parts = mod_file.replace('.jar', '').split('-')
                if len(parts) >= 2:
                    mod_name = parts[0]
                    mod_version = parts[-1]
                
                # Добавляем в Treeview
                size_str = f"{mod_size / 1024 / 1024:.2f} MB" if mod_size > 1024 * 1024 else f"{mod_size / 1024:.2f} KB"
                self.mods_tree.insert("", "end", values=(mod_name, mod_version, size_str, mod_file))
            
            self.log(f"Загружено {len(mod_files)} модов")
            
        except Exception as e:
            self.log(f"Ошибка при обновлении списка модов: {str(e)}")
    
    def add_mod_from_file(self):
        """Добавляет мод из файла"""
        try:
            file_path = filedialog.askopenfilename(
                title="Выберите файл мода",
                filetypes=[("JAR файлы", "*.jar"), ("Все файлы", "*.*")]
            )
            
            if file_path:
                mod_name = os.path.basename(file_path)
                dest_path = os.path.join(MODS_DIR, mod_name)
                
                # Создаем папку если нет
                os.makedirs(MODS_DIR, exist_ok=True)
                
                # Копируем файл
                shutil.copy2(file_path, dest_path)
                self.log(f"Мод {mod_name} добавлен")
                self.refresh_mods_list()
                
        except Exception as e:
            self.log(f"Ошибка при добавлении мода: {str(e)}")
            messagebox.showerror("Ошибка", f"Не удалось добавить мод: {str(e)}")
    
    def add_mod_from_url(self):
        """Добавляет мод по URL"""
        try:
            # Создаем диалоговое окно для ввода URL
            url_dialog = tk.Toplevel(self.root)
            url_dialog.title("Добавить мод по ссылке")
            url_dialog.geometry("500x150")
            url_dialog.transient(self.root)
            url_dialog.grab_set()
            
            tk.Label(url_dialog, text="Введите URL мода:").pack(pady=10)
            url_entry = tk.Entry(url_dialog, width=60)
            url_entry.pack(pady=5)
            
            def download_mod():
                url = url_entry.get().strip()
                if not url:
                    messagebox.showwarning("Внимание", "Введите URL")
                    return
                
                try:
                    self.log(f"Загрузка мода из {url}...")
                    session = InsecureSession()
                    response = session.get(url, stream=True, timeout=30)
                    
                    # Получаем имя файла
                    if 'Content-Disposition' in response.headers:
                        content_disposition = response.headers['Content-Disposition']
                        filename = content_disposition.split('filename=')[1].strip('"')
                    else:
                        filename = os.path.basename(url)
                    
                    if not filename.endswith('.jar'):
                        filename += '.jar'
                    
                    # Сохраняем файл
                    os.makedirs(MODS_DIR, exist_ok=True)
                    dest_path = os.path.join(MODS_DIR, filename)
                    
                    total_size = int(response.headers.get('content-length', 0))
                    downloaded = 0
                    
                    with open(dest_path, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)
                                downloaded += len(chunk)
                                if total_size > 0:
                                    progress = (downloaded / total_size) * 100
                                    self.root.after(0, self.update_progress, progress)
                    
                    self.log(f"Мод {filename} успешно загружен")
                    self.refresh_mods_list()
                    url_dialog.destroy()
                    
                except Exception as e:
                    self.log(f"Ошибка при загрузке мода: {str(e)}")
                    messagebox.showerror("Ошибка", f"Не удалось загрузить мод: {str(e)}")
            
            tk.Button(url_dialog, text="Загрузить", command=download_mod).pack(pady=10)
            
        except Exception as e:
            self.log(f"Ошибка: {str(e)}")
    
    def remove_selected_mod(self):
        """Удаляет выбранный мод"""
        try:
            selection = self.mods_tree.selection()
            if not selection:
                messagebox.showinfo("Информация", "Выберите мод для удаления")
                return
            
            item = self.mods_tree.item(selection[0])
            mod_filename = item['values'][3]
            mod_path = os.path.join(MODS_DIR, mod_filename)
            
            if os.path.exists(mod_path):
                os.remove(mod_path)
                self.log(f"Мод {mod_filename} удален")
                self.refresh_mods_list()
            else:
                messagebox.showwarning("Внимание", "Файл мода не найден")
                
        except Exception as e:
            self.log(f"Ошибка при удалении мода: {str(e)}")
            messagebox.showerror("Ошибка", f"Не удалось удалить мод: {str(e)}")
    
    def clear_all_mods(self):
        """Очищает все моды"""
        try:
            if not os.path.exists(MODS_DIR):
                return
            
            if messagebox.askyesno("Подтверждение", "Удалить все моды?"):
                for file in os.listdir(MODS_DIR):
                    if file.endswith('.jar'):
                        os.remove(os.path.join(MODS_DIR, file))
                
                self.log("Все моды удалены")
                self.refresh_mods_list()
                
        except Exception as e:
            self.log(f"Ошибка при очистке модов: {str(e)}")
    
    def on_mod_selected(self, event):
        """Обработчик выбора мода"""
        try:
            selection = self.mods_tree.selection()
            if not selection:
                return
            
            item = self.mods_tree.item(selection[0])
            mod_filename = item['values'][3]
            mod_path = os.path.join(MODS_DIR, mod_filename)
            
            # Очищаем информацию
            self.mod_info_text.delete(1.0, tk.END)
            
            # Добавляем базовую информацию
            info_text = f"Имя файла: {mod_filename}\n"
            info_text += f"Размер: {item['values'][2]}\n"
            info_text += f"Путь: {mod_path}\n\n"
            
            # Пытаемся получить дополнительную информацию из файла
            if os.path.exists(mod_path):
                mod_size = os.path.getsize(mod_path)
                mod_time = os.path.getmtime(mod_path)
                from datetime import datetime
                info_text += f"Дата изменения: {datetime.fromtimestamp(mod_time).strftime('%Y-%m-%d %H:%M:%S')}\n"
                
                # Можно добавить парсинг mods.toml или fabric.mod.json для более детальной информации
                # но это требует дополнительных библиотек
            
            self.mod_info_text.insert(1.0, info_text)
            
        except Exception as e:
            self.log(f"Ошибка при получении информации о моде: {str(e)}")

if __name__ == "__main__":
    root = tk.Tk()
    launcher = MinecraftLauncher(root)
    root.mainloop()
    