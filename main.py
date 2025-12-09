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
from datetime import datetime

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
MODPACKS_DIR = os.path.join(MINECRAFT_DIR, "modpacks")
MODS_CACHE_DIR = os.path.join(MINECRAFT_DIR, "mods_cache")

class MinecraftLauncher:
    def __init__(self, root):
        self.root = root
        self.root.title("Minecraft Launcher")
        self.root.geometry("900x750")
        self.root.configure(bg='#2b2b2b')
        
        # Применяем темную тему
        self.setup_dark_theme()
        
        # Создаем директории
        os.makedirs(MODPACKS_DIR, exist_ok=True)
        os.makedirs(MODS_CACHE_DIR, exist_ok=True)
        
        # Текущий выбранный модпак
        self.current_modpack = None
        
        # Создаем Notebook для вкладок
        style = ttk.Style()
        style.configure('Custom.TNotebook', background='#2b2b2b', borderwidth=0)
        style.configure('Custom.TNotebook.Tab', 
                       background='#3c3c3c', 
                       foreground='white',
                       padding=[10, 5])
        style.map('Custom.TNotebook.Tab', 
                 background=[('selected', '#4a4a4a')],
                 foreground=[('selected', 'white')])
        
        self.notebook = ttk.Notebook(root, style='Custom.TNotebook')
        self.notebook.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Основная вкладка
        self.main_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.main_frame, text="Основная")
        
        # Вкладка модов
        self.mods_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.mods_frame, text="Моды")
        
        # Вкладка модпаков
        self.modpacks_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.modpacks_frame, text="Модпаки")
        
        self.setup_main_tab()
        self.setup_mods_tab()
        self.setup_modpacks_tab()
        
        # Словарь для хранения информации о модлоадерах
        self.modloader_versions = {
            "Forge": [],
            "NeoForge": [],
            "Fabric": [],
            "Quilt": []
        }
        
        # Загружаем версии
        self.refresh_versions()
        
        # Загружаем список модпаков
        self.refresh_modpacks_list()
        # В конце __init__ метода добавьте:
# Настройка возможности изменения размера разделителей
        self.root.update()
        paned_sash_positions = {}
    
    def setup_dark_theme(self):
        """Настройка темной темы"""
        style = ttk.Style()
        
        # Цвета для темной темы
        bg_color = '#2b2b2b'
        fg_color = '#ffffff'
        entry_bg = '#3c3c3c'
        button_bg = '#4a4a4a'
        accent_color = '#4a76b8'
        
        style.theme_use('default')
        
        # Настраиваем стили для PanedWindow
        self.root.option_add('*PanedWindow.background', bg_color)
        self.root.option_add('*PanedWindow.sashwidth', 5)
        self.root.option_add('*PanedWindow.sashrelief', 'raised')
        self.root.option_add('*PanedWindow.sashpad', 0)
        
        # Настраиваем стили
        style.configure('TFrame', background=bg_color)
        style.configure('TLabel', background=bg_color, foreground=fg_color, font=('Segoe UI', 10))
        style.configure('TButton', 
                       background=button_bg, 
                       foreground=fg_color,
                       borderwidth=1,
                       relief='raised',
                       font=('Segoe UI', 10))
        style.map('TButton',
                 background=[('active', '#5a5a5a'), ('pressed', '#3a3a3a')],
                 foreground=[('active', 'white')])
        
        style.configure('TEntry', 
                       fieldbackground=entry_bg,
                       foreground=fg_color,
                       insertcolor=fg_color,
                       borderwidth=1,
                       relief='sunken')
        
        style.configure('TCombobox', 
                       fieldbackground=entry_bg,
                       background=entry_bg,
                       foreground=fg_color,
                       arrowcolor=fg_color)
        
        style.configure('Vertical.TScrollbar', 
                       background=button_bg,
                       troughcolor=bg_color,
                       borderwidth=0)
        
        style.configure('Horizontal.TScrollbar', 
                       background=button_bg,
                       troughcolor=bg_color,
                       borderwidth=0)
        
        # Стиль для Treeview
        style.configure('Treeview',
                       background=entry_bg,
                       foreground=fg_color,
                       fieldbackground=entry_bg,
                       rowheight=25)
        style.configure('Treeview.Heading',
                       background=button_bg,
                       foreground=fg_color,
                       relief='flat',
                       font=('Segoe UI', 10, 'bold'))
        style.map('Treeview',
                 background=[('selected', accent_color)],
                 foreground=[('selected', 'white')])
    
    def setup_main_tab(self):
        """Настройка основной вкладки"""
        # Основной контейнер с прокруткой
        main_container = ttk.Frame(self.main_frame)
        main_container.pack(fill="both", expand=True)
        
        canvas = tk.Canvas(main_container, bg='#2b2b2b', highlightthickness=0)
        scrollbar = ttk.Scrollbar(main_container, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Заголовок с предупреждением об SSL
        warning_label = tk.Label(scrollable_frame, 
                               text="ВНИМАНИЕ: SSL проверка отключена!", 
                               fg="#ff6b6b", 
                               bg='#2b2b2b',
                               font=("Segoe UI", 10, "bold"))
        warning_label.pack(pady=10, padx=20)
        
        # Блок выбора версии
        version_block = ttk.LabelFrame(scrollable_frame, text="Выбор версии", padding=15)
        version_block.pack(fill="x", padx=20, pady=10)
        
        # Фрейм для выбора версии Minecraft
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
                                       command=self.refresh_versions)
        self.refresh_button.pack(side="left")
        
        # Фрейм для выбора модлоадера
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
        
        # Блок данных аккаунта
        account_block = ttk.LabelFrame(scrollable_frame, text="Данные аккаунта", padding=15)
        account_block.pack(fill="x", padx=20, pady=10)
        
        # Поле для имени пользователя
        username_frame = ttk.Frame(account_block)
        username_frame.pack(fill="x", pady=5)
        ttk.Label(username_frame, text="Имя пользователя:").pack(side="left", padx=(0, 10))
        self.username_entry = ttk.Entry(username_frame, width=30)
        self.username_entry.insert(0, "Player")
        self.username_entry.pack(side="left", fill="x", expand=True)
        
        # Поле для UUID
        uuid_frame = ttk.Frame(account_block)
        uuid_frame.pack(fill="x", pady=5)
        ttk.Label(uuid_frame, text="UUID (опционально):").pack(side="left", padx=(0, 10))
        self.uuid_entry = ttk.Entry(uuid_frame, width=40)
        self.uuid_entry.pack(side="left", fill="x", expand=True)
        
        # Поле для токена
        token_frame = ttk.Frame(account_block)
        token_frame.pack(fill="x", pady=5)
        ttk.Label(token_frame, text="Token (опционально):").pack(side="left", padx=(0, 10))
        self.token_entry = ttk.Entry(token_frame, width=40, show="*")
        self.token_entry.pack(side="left", fill="x", expand=True)
        
        # Кнопка для показа/скрытия токена
        self.show_token_var = tk.BooleanVar()
        self.show_token_check = ttk.Checkbutton(token_frame, 
                                              text="Показать", 
                                              variable=self.show_token_var,
                                              command=self.toggle_token_visibility)
        self.show_token_check.pack(side="left", padx=(10, 0))
        
        # Блок прогресса
        progress_block = ttk.LabelFrame(scrollable_frame, text="Прогресс установки", padding=15)
        progress_block.pack(fill="x", padx=20, pady=10)
        
        # Прогресс-бар с исправлением
        self.progress_var = tk.DoubleVar()
        self.progress = ttk.Progressbar(progress_block, 
                                      mode='determinate',
                                      variable=self.progress_var,
                                      length=100)
        self.progress.pack(fill="x", pady=5)
        
        self.progress_label = ttk.Label(progress_block, text="Готов к установке")
        self.progress_label.pack()
        
        # Блок управления
        control_block = ttk.Frame(scrollable_frame)
        control_block.pack(fill="x", padx=20, pady=10)
        
        # Кнопка установки
        self.install_button = tk.Button(control_block, 
                                      text="Установить", 
                                      command=self.install_version,
                                      bg='#4a76b8',
                                      fg='white',
                                      font=("Segoe UI", 10, "bold"),
                                      relief="flat",
                                      padx=20,
                                      pady=10,
                                      cursor="hand2")
        self.install_button.pack(side="left", padx=(0, 10))
        
        # Кнопка запуска
        self.launch_button = tk.Button(control_block, 
                                     text="🚀 Запуск Minecraft", 
                                     command=self.launch_minecraft,
                                     bg='#27ae60',
                                     fg='white',
                                     font=("Segoe UI", 10, "bold"),
                                     relief="flat",
                                     padx=20,
                                     pady=10,
                                     cursor="hand2")
        self.launch_button.pack(side="left")
        
        # Блок логов
        log_block = ttk.LabelFrame(scrollable_frame, text="Логи установки", padding=10)
        log_block.pack(fill="both", expand=True, padx=20, pady=10)
        
        # Текстовое поле для логов с темной темой
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
        
        # Статус бар
        status_frame = ttk.Frame(scrollable_frame)
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
    
    def setup_mods_tab(self):
        """Настройка вкладки модов"""
        # Основной контейнер
        main_container = ttk.Frame(self.mods_frame)
        main_container.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Панель управления
        control_frame = ttk.LabelFrame(main_container, text="Управление модами", padding=10)
        control_frame.pack(fill="x", pady=(0, 10))
        
        # Кнопки управления
        button_frame = ttk.Frame(control_frame)
        button_frame.pack()
        
        self.add_mod_button = tk.Button(button_frame, 
                                    text="📁 Добавить из файла", 
                                    command=self.add_mod_from_file,
                                    bg='#4a76b8',
                                    fg='white',
                                    relief="flat",
                                    padx=15,
                                    pady=5)
        self.add_mod_button.pack(side="left", padx=5)
        
        self.add_mod_url_button = tk.Button(button_frame, 
                                        text="🔗 Добавить по ссылке", 
                                        command=self.add_mod_from_url,
                                        bg='#4a76b8',
                                        fg='white',
                                        relief="flat",
                                        padx=15,
                                        pady=5)
        self.add_mod_url_button.pack(side="left", padx=5)
        
        self.remove_mod_button = tk.Button(button_frame, 
                                        text="🗑️ Удалить выбранный", 
                                        command=self.remove_selected_mod,
                                        bg='#e74c3c',
                                        fg='white',
                                        relief="flat",
                                        padx=15,
                                        pady=5)
        self.remove_mod_button.pack(side="left", padx=5)
        
        self.clear_mods_button = tk.Button(button_frame, 
                                        text="🧹 Очистить все", 
                                        command=self.clear_all_mods,
                                        bg='#e74c3c',
                                        fg='white',
                                        relief="flat",
                                        padx=15,
                                        pady=5)
        self.clear_mods_button.pack(side="left", padx=5)
        
        self.refresh_mods_button = tk.Button(button_frame, 
                                        text="🔄 Обновить", 
                                        command=self.refresh_mods_list,
                                        bg='#3498db',
                                        fg='white',
                                        relief="flat",
                                        padx=15,
                                        pady=5)
        self.refresh_mods_button.pack(side="left", padx=5)
        
        # Информация о текущем модпаке
        self.current_modpack_label = ttk.Label(control_frame, 
                                            text="Текущий модпак: Не выбран",
                                            font=("Segoe UI", 9, "italic"))
        self.current_modpack_label.pack(pady=(10, 0))
        
        # Основной контент с прокруткой
        content_container = ttk.Frame(main_container)
        content_container.pack(fill="both", expand=True)
        
        # Используем PanedWindow для разделения на две части с возможностью изменения размера
        paned = tk.PanedWindow(content_container, orient=tk.HORIZONTAL, bg='#2b2b2b', sashwidth=5)
        paned.pack(fill="both", expand=True)
        
        # Список модов (левая часть)
        list_frame = ttk.LabelFrame(paned, text="Список модов", padding=10)
        
        # Treeview для модов
        columns = ("Название", "Версия", "Размер", "Файл")
        self.mods_tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=15)
        
        # Настройка колонок
        self.mods_tree.heading("Название", text="Название", anchor="w")
        self.mods_tree.heading("Версия", text="Версия", anchor="center")
        self.mods_tree.heading("Размер", text="Размер", anchor="center")
        self.mods_tree.heading("Файл", text="Файл", anchor="w")
        
        self.mods_tree.column("Название", width=200)
        self.mods_tree.column("Версия", width=80, anchor="center")
        self.mods_tree.column("Размер", width=80, anchor="center")
        self.mods_tree.column("Файл", width=150)
        
        # Скроллбар
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.mods_tree.yview)
        self.mods_tree.configure(yscrollcommand=scrollbar.set)
        
        self.mods_tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Информация о моде (правая часть)
        info_frame = ttk.LabelFrame(paned, text="Информация о моде", padding=10)
        
        self.mod_info_text = tk.Text(info_frame, 
                                height=20, 
                                wrap="word",
                                bg='#3c3c3c',
                                fg='#ffffff',
                                insertbackground='white',
                                font=("Segoe UI", 9),
                                width=40)  # Фиксированная ширина в символах
        mod_info_scrollbar = ttk.Scrollbar(info_frame, command=self.mod_info_text.yview)
        self.mod_info_text.config(yscrollcommand=mod_info_scrollbar.set)
        
        self.mod_info_text.pack(side="left", fill="both", expand=True)
        mod_info_scrollbar.pack(side="right", fill="y")
        
        # Добавляем фреймы в PanedWindow
        paned.add(list_frame, width=500, minsize=300)  # Левая часть шире
        paned.add(info_frame, width=300, minsize=200)  # Правая часть уже
        
        # Привязываем событие выбора мода
        self.mods_tree.bind("<<TreeviewSelect>>", self.on_mod_selected)
        
        # Загружаем список модов
        self.refresh_mods_list()
    
    def setup_modpacks_tab(self):
        """Настройка вкладки модпаков"""
        # Основной контейнер
        main_container = ttk.Frame(self.modpacks_frame)
        main_container.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Панель управления модпаками
        control_frame = ttk.LabelFrame(main_container, text="Управление модпаками", padding=10)
        control_frame.pack(fill="x", pady=(0, 10))
        
        # Кнопки управления
        button_frame = ttk.Frame(control_frame)
        button_frame.pack()
        
        self.create_modpack_button = tk.Button(button_frame,
                                            text="➕ Создать модпак",
                                            command=self.create_modpack_dialog,
                                            bg='#27ae60',
                                            fg='white',
                                            relief="flat",
                                            padx=15,
                                            pady=5)
        self.create_modpack_button.pack(side="left", padx=5)
        
        self.delete_modpack_button = tk.Button(button_frame,
                                            text="🗑️ Удалить модпак",
                                            command=self.delete_modpack,
                                            bg='#e74c3c',
                                            fg='white',
                                            relief="flat",
                                            padx=15,
                                            pady=5)
        self.delete_modpack_button.pack(side="left", padx=5)
        
        self.export_modpack_button = tk.Button(button_frame,
                                            text="📤 Экспорт модпака",
                                            command=self.export_modpack,
                                            bg='#3498db',
                                            fg='white',
                                            relief="flat",
                                            padx=15,
                                            pady=5)
        self.export_modpack_button.pack(side="left", padx=5)
        
        self.refresh_modpacks_button = tk.Button(button_frame,
                                            text="🔄 Обновить",
                                            command=self.refresh_modpacks_list,
                                            bg='#3498db',
                                            fg='white',
                                            relief="flat",
                                            padx=15,
                                            pady=5)
        self.refresh_modpacks_button.pack(side="left", padx=5)
        
        # Основной контент с прокруткой
        content_container = ttk.Frame(main_container)
        content_container.pack(fill="both", expand=True, pady=(0, 10))
        
        # Используем PanedWindow для разделения
        paned = tk.PanedWindow(content_container, orient=tk.HORIZONTAL, bg='#2b2b2b', sashwidth=5)
        paned.pack(fill="both", expand=True)
        
        # Список модпаков (левая часть)
        list_frame = ttk.LabelFrame(paned, text="Список модпаков", padding=10)
        
        # Treeview для модпаков
        columns = ("Название", "Версия игры", "Модлоадер", "Кол-во модов", "Дата создания")
        self.modpacks_tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=10)
        
        # Настройка колонок
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
        
        # Скроллбар
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.modpacks_tree.yview)
        self.modpacks_tree.configure(yscrollcommand=scrollbar.set)
        
        self.modpacks_tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Информация о модпаке (правая часть)
        info_frame = ttk.LabelFrame(paned, text="Информация о модпаке", padding=10)
        
        self.modpack_info_text = tk.Text(info_frame,
                                    height=10,
                                    wrap="word",
                                    bg='#3c3c3c',
                                    fg='#ffffff',
                                    insertbackground='white',
                                    font=("Segoe UI", 9),
                                    width=40)
        modpack_info_scrollbar = ttk.Scrollbar(info_frame, command=self.modpack_info_text.yview)
        self.modpack_info_text.config(yscrollcommand=modpack_info_scrollbar.set)
        
        self.modpack_info_text.pack(side="left", fill="both", expand=True)
        modpack_info_scrollbar.pack(side="right", fill="y")
        
        # Добавляем фреймы в PanedWindow
        paned.add(list_frame, width=550, minsize=400)  # Левая часть шире
        paned.add(info_frame, width=350, minsize=250)  # Правая часть уже
        
        # Привязываем событие выбора модпака
        self.modpacks_tree.bind("<<TreeviewSelect>>", self.on_modpack_selected)
        
        # Загружаем список модпаков
        self.refresh_modpacks_list()
    
    def toggle_token_visibility(self):
        """Переключает видимость токена"""
        if self.show_token_var.get():
            self.token_entry.config(show="")
        else:
            self.token_entry.config(show="*")
    
    def log(self, message):
        """Добавляет сообщение в лог"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)
        self.root.update_idletasks()
    
    def set_status(self, message):
        """Устанавливает статус"""
        self.status_var.set(message)
        self.root.update_idletasks()
    
    def update_progress(self, value, max_value=None):
        """Обновляет прогресс-бар (исправленная версия)"""
        if max_value is not None and max_value > 0:
            progress_percent = (value / max_value) * 100
            self.progress_var.set(progress_percent)
            self.progress_label.config(text=f"Прогресс: {progress_percent:.1f}%")
        else:
            # Если передано только одно значение, считаем его процентом
            self.progress_var.set(value)
            self.progress_label.config(text=f"Прогресс: {value:.1f}%")
        
        self.root.update_idletasks()
    
    def refresh_versions(self):
        """Обновляет список версий"""
        self.refresh_button.config(state="disabled")
        self.set_status("Загрузка списка версий...")
        threading.Thread(target=self.load_versions, daemon=True).start()
    
    def load_versions(self):
        """Загружает список версий Minecraft"""
        try:
            self.log("Получение списка версий Minecraft...")
            
            # Пробуем несколько источников
            urls = [
                "https://launchermeta.mojang.com/mc/game/version_manifest_v2.json",
                "https://piston-meta.mojang.com/mc/game/version_manifest_v2.json"
            ]
            
            version_data = None
            session = InsecureSession()
            
            for url in urls:
                try:
                    response = session.get(url, timeout=30)
                    if response.status_code == 200:
                        version_data = response.json()
                        break
                except:
                    continue
            
            if not version_data:
                raise Exception("Не удалось загрузить список версий")
            
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
            # Локальный список версий для тестирования
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
                    self.modloader_versions["Fabric"] = fabric_versions[:50]
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
            
            # Callback для отслеживания прогресса (исправленная версия)
            callback = {
                'setStatus': lambda text: self.root.after(0, self.set_status, text),
                'setProgress': lambda value: self.root.after(0, self.update_progress, value),
                'setMax': lambda max_value: None  # Игнорируем установку максимума
            }
            
            # Устанавливаем Minecraft
            mclib.install.install_minecraft_version(minecraft_version, MINECRAFT_DIR, callback=callback)
            self.log(f"Minecraft {minecraft_version} успешно установлен!")
            
            # Устанавливаем модлоадер если нужно
            if modloader != "Vanilla":
                self.install_modloader(minecraft_version, modloader, modloader_version, callback)
            
            self.set_status(f"Установка завершена")
            self.update_progress(0)  # Сбрасываем прогресс-бар
            self.root.after(0, lambda: self.install_button.config(state="normal"))
            self.root.after(0, lambda: self.launch_button.config(state="normal"))
            
        except Exception as e:
            self.log(f"Ошибка при установке: {str(e)}")
            self.set_status("Ошибка установки")
            self.update_progress(0)
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
            
            # Если выбран модпак, используем его папку для модов
            if self.current_modpack:
                modpack_mods_dir = os.path.join(MODPACKS_DIR, self.current_modpack, "mods")
                if os.path.exists(modpack_mods_dir):
                    # Копируем моды из модпака в рабочую папку
                    working_mods_dir = os.path.join(MINECRAFT_DIR, "mods")
                    os.makedirs(working_mods_dir, exist_ok=True)
                    
                    # Очищаем рабочую папку
                    for file in os.listdir(working_mods_dir):
                        if file.endswith('.jar'):
                            os.remove(os.path.join(working_mods_dir, file))
                    
                    # Копируем моды из модпака
                    for file in os.listdir(modpack_mods_dir):
                        if file.endswith('.jar'):
                            shutil.copy2(os.path.join(modpack_mods_dir, file), 
                                       os.path.join(working_mods_dir, file))
            
            # Добавляем путь к папке с модами
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
            
            # Определяем директорию для модов
            if self.current_modpack:
                mods_dir = os.path.join(MODPACKS_DIR, self.current_modpack, "mods")
            else:
                mods_dir = os.path.join(MINECRAFT_DIR, "mods")
            
            # Проверяем существование папки модов
            if not os.path.exists(mods_dir):
                os.makedirs(mods_dir, exist_ok=True)
                return
            
            # Загружаем моды из папки
            mod_files = [f for f in os.listdir(mods_dir) if f.endswith('.jar')]
            
            for mod_file in mod_files:
                mod_path = os.path.join(mods_dir, mod_file)
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
                if mod_size > 1024 * 1024:
                    size_str = f"{mod_size / 1024 / 1024:.1f} MB"
                else:
                    size_str = f"{mod_size / 1024:.0f} KB"
                
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
                
                # Определяем директорию для сохранения
                if self.current_modpack:
                    dest_dir = os.path.join(MODPACKS_DIR, self.current_modpack, "mods")
                else:
                    dest_dir = os.path.join(MINECRAFT_DIR, "mods")
                
                os.makedirs(dest_dir, exist_ok=True)
                dest_path = os.path.join(dest_dir, mod_name)
                
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
            url_dialog.configure(bg='#2b2b2b')
            url_dialog.transient(self.root)
            url_dialog.grab_set()
            
            # Центрируем окно
            url_dialog.update_idletasks()
            x = self.root.winfo_x() + (self.root.winfo_width() - url_dialog.winfo_width()) // 2
            y = self.root.winfo_y() + (self.root.winfo_height() - url_dialog.winfo_height()) // 2
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
                    
                    # Определяем директорию для сохранения
                    if self.current_modpack:
                        dest_dir = os.path.join(MODPACKS_DIR, self.current_modpack, "mods")
                    else:
                        dest_dir = os.path.join(MINECRAFT_DIR, "mods")
                    
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
                                    self.root.after(0, self.update_progress, progress)
                    
                    self.log(f"Мод {filename} успешно загружен")
                    self.refresh_mods_list()
                    url_dialog.destroy()
                    
                except Exception as e:
                    self.log(f"Ошибка при загрузке мода: {str(e)}")
                    messagebox.showerror("Ошибка", f"Не удалось загрузить мод: {str(e)}")
            
            button_frame = ttk.Frame(url_dialog)
            button_frame.pack(pady=10)
            
            ttk.Button(button_frame, text="Загрузить", command=download_mod).pack(side="left", padx=5)
            ttk.Button(button_frame, text="Отмена", command=url_dialog.destroy).pack(side="left", padx=5)
            
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
            
            # Определяем директорию с модами
            if self.current_modpack:
                mod_dir = os.path.join(MODPACKS_DIR, self.current_modpack, "mods")
            else:
                mod_dir = os.path.join(MINECRAFT_DIR, "mods")
            
            mod_path = os.path.join(mod_dir, mod_filename)
            
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
            # Определяем директорию с модами
            if self.current_modpack:
                mod_dir = os.path.join(MODPACKS_DIR, self.current_modpack, "mods")
            else:
                mod_dir = os.path.join(MINECRAFT_DIR, "mods")
            
            if not os.path.exists(mod_dir):
                return
            
            if messagebox.askyesno("Подтверждение", "Удалить все моды?"):
                for file in os.listdir(mod_dir):
                    if file.endswith('.jar'):
                        os.remove(os.path.join(mod_dir, file))
                
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
            
            # Определяем директорию с модами
            if self.current_modpack:
                mod_dir = os.path.join(MODPACKS_DIR, self.current_modpack, "mods")
            else:
                mod_dir = os.path.join(MINECRAFT_DIR, "mods")
            
            mod_path = os.path.join(mod_dir, mod_filename)
            
            # Очищаем информацию
            self.mod_info_text.delete(1.0, tk.END)
            
            if os.path.exists(mod_path):
                mod_size = os.path.getsize(mod_path)
                mod_time = os.path.getmtime(mod_path)
                
                info_text = f"📁 Имя файла: {mod_filename}\n\n"
                info_text += f"📊 Размер: {item['values'][2]}\n"
                info_text += f"📅 Дата изменения: {datetime.fromtimestamp(mod_time).strftime('%Y-%m-%d %H:%M:%S')}\n"
                info_text += f"📍 Путь: {mod_path}\n\n"
                
                # Базовый анализ JAR файла
                try:
                    import zipfile
                    with zipfile.ZipFile(mod_path, 'r') as zip_ref:
                        # Ищем файлы с информацией о моде
                        for file_info in zip_ref.infolist():
                            filename = file_info.filename
                            if 'fabric.mod.json' in filename or 'mods.toml' in filename or 'mcmod.info' in filename:
                                info_text += f"📄 Конфигурационный файл: {filename}\n"
                                break
                except:
                    pass
                
                self.mod_info_text.insert(1.0, info_text)
            
        except Exception as e:
            self.log(f"Ошибка при получении информации о моде: {str(e)}")
    
    # ===== ФУНКЦИИ ДЛЯ РАБОТЫ С МОДПАКАМИ =====
    
    def refresh_modpacks_list(self):
        """Обновляет список модпаков"""
        try:
            # Очищаем Treeview
            for item in self.modpacks_tree.get_children():
                self.modpacks_tree.delete(item)
            
            # Проверяем существование папки модпаков
            if not os.path.exists(MODPACKS_DIR):
                os.makedirs(MODPACKS_DIR, exist_ok=True)
                return
            
            # Загружаем модпаки
            modpack_folders = [f for f in os.listdir(MODPACKS_DIR) 
                             if os.path.isdir(os.path.join(MODPACKS_DIR, f))]
            
            for modpack in modpack_folders:
                modpack_path = os.path.join(MODPACKS_DIR, modpack)
                info_file = os.path.join(modpack_path, "modpack_info.json")
                
                # Читаем информацию о модпаке
                if os.path.exists(info_file):
                    try:
                        with open(info_file, 'r', encoding='utf-8') as f:
                            info = json.load(f)
                    except:
                        info = {}
                else:
                    info = {}
                
                # Количество модов
                mods_dir = os.path.join(modpack_path, "mods")
                mod_count = 0
                if os.path.exists(mods_dir):
                    mod_count = len([f for f in os.listdir(mods_dir) if f.endswith('.jar')])
                
                # Добавляем в Treeview
                self.modpacks_tree.insert("", "end", values=(
                    info.get('name', modpack),
                    info.get('minecraft_version', 'Не указана'),
                    info.get('modloader', 'Не указан'),
                    str(mod_count),
                    info.get('created', 'Не указана')
                ))
            
            self.log(f"Загружено {len(modpack_folders)} модпаков")
            
        except Exception as e:
            self.log(f"Ошибка при обновлении списка модпаков: {str(e)}")
    
    def create_modpack_dialog(self):
        """Диалог создания нового модпака"""
        try:
            dialog = tk.Toplevel(self.root)
            dialog.title("Создание нового модпака")
            dialog.geometry("400x300")
            dialog.configure(bg='#2b2b2b')
            dialog.transient(self.root)
            dialog.grab_set()
            
            # Центрируем окно
            dialog.update_idletasks()
            x = self.root.winfo_x() + (self.root.winfo_width() - dialog.winfo_width()) // 2
            y = self.root.winfo_y() + (self.root.winfo_height() - dialog.winfo_height()) // 2
            dialog.geometry(f"+{x}+{y}")
            
            # Заголовок
            tk.Label(dialog, 
                    text="Создание нового модпака", 
                    bg='#2b2b2b', 
                    fg='white',
                    font=("Segoe UI", 12, "bold")).pack(pady=20)
            
            # Поле для имени
            name_frame = ttk.Frame(dialog)
            name_frame.pack(fill="x", padx=30, pady=10)
            
            ttk.Label(name_frame, text="Название модпака:").pack(anchor="w")
            name_entry = ttk.Entry(name_frame)
            name_entry.pack(fill="x", pady=5)
            
            # Поле для описания
            desc_frame = ttk.Frame(dialog)
            desc_frame.pack(fill="x", padx=30, pady=10)
            
            ttk.Label(desc_frame, text="Описание (опционально):").pack(anchor="w")
            desc_entry = tk.Text(desc_frame, height=4, width=40)
            desc_entry.pack(fill="x", pady=5)
            
            def create_modpack():
                name = name_entry.get().strip()
                if not name:
                    messagebox.showwarning("Внимание", "Введите название модпака")
                    return
                
                # Заменяем недопустимые символы в имени
                safe_name = "".join(c for c in name if c.isalnum() or c in (' ', '-', '_')).strip()
                if not safe_name:
                    safe_name = "new_modpack"
                
                # Создаем модпак
                self.create_modpack(safe_name, desc_entry.get("1.0", tk.END).strip())
                dialog.destroy()
            
            # Кнопки
            button_frame = ttk.Frame(dialog)
            button_frame.pack(pady=20)
            
            ttk.Button(button_frame, text="Создать", command=create_modpack).pack(side="left", padx=5)
            ttk.Button(button_frame, text="Отмена", command=dialog.destroy).pack(side="left", padx=5)
            
        except Exception as e:
            self.log(f"Ошибка при создании диалога: {str(e)}")
    
    def create_modpack(self, name, description=""):
        """Создает новый модпак"""
        try:
            # Создаем папку модпака
            modpack_path = os.path.join(MODPACKS_DIR, name)
            os.makedirs(modpack_path, exist_ok=True)
            
            # Создаем подпапки
            os.makedirs(os.path.join(modpack_path, "mods"), exist_ok=True)
            os.makedirs(os.path.join(modpack_path, "config"), exist_ok=True)
            os.makedirs(os.path.join(modpack_path, "resourcepacks"), exist_ok=True)
            os.makedirs(os.path.join(modpack_path, "shaderpacks"), exist_ok=True)
            
            # Создаем файл с информацией
            info = {
                'name': name,
                'description': description,
                'created': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'minecraft_version': self.version_var.get(),
                'modloader': self.modloader_var.get(),
                'modloader_version': self.modloader_version_var.get()
            }
            
            with open(os.path.join(modpack_path, "modpack_info.json"), 'w', encoding='utf-8') as f:
                json.dump(info, f, ensure_ascii=False, indent=2)
            
            # Устанавливаем текущий модпак
            self.current_modpack = name
            self.current_modpack_label.config(text=f"Текущий модпак: {name}")
            
            self.log(f"Создан модпак: {name}")
            self.refresh_modpacks_list()
            self.refresh_mods_list()
            
            messagebox.showinfo("Успех", f"Модпак '{name}' успешно создан!")
            
        except Exception as e:
            self.log(f"Ошибка при создании модпака: {str(e)}")
            messagebox.showerror("Ошибка", f"Не удалось создать модпак: {str(e)}")
    
    def delete_modpack(self):
        """Удаляет выбранный модпак"""
        try:
            selection = self.modpacks_tree.selection()
            if not selection:
                messagebox.showinfo("Информация", "Выберите модпак для удаления")
                return
            
            item = self.modpacks_tree.item(selection[0])
            modpack_name = item['values'][0]
            
            if messagebox.askyesno("Подтверждение", 
                                 f"Удалить модпак '{modpack_name}'?\nЭто действие нельзя отменить!"):
                modpack_path = os.path.join(MODPACKS_DIR, modpack_name)
                
                if os.path.exists(modpack_path):
                    shutil.rmtree(modpack_path)
                    
                    # Если удаляемый модпак был текущим, сбрасываем выбор
                    if self.current_modpack == modpack_name:
                        self.current_modpack = None
                        self.current_modpack_label.config(text="Текущий модпак: Не выбран")
                        self.refresh_mods_list()
                    
                    self.log(f"Модпак '{modpack_name}' удален")
                    self.refresh_modpacks_list()
                    
        except Exception as e:
            self.log(f"Ошибка при удалении модпака: {str(e)}")
            messagebox.showerror("Ошибка", f"Не удалось удалить модпак: {str(e)}")
    
    def export_modpack(self):
        """Экспортирует модпак в архив"""
        try:
            selection = self.modpacks_tree.selection()
            if not selection:
                messagebox.showinfo("Информация", "Выберите модпак для экспорта")
                return
            
            item = self.modpacks_tree.item(selection[0])
            modpack_name = item['values'][0]
            
            # Выбираем место для сохранения
            filename = filedialog.asksaveasfilename(
                title="Экспорт модпака",
                defaultextension=".zip",
                filetypes=[("ZIP архив", "*.zip"), ("Все файлы", "*.*")],
                initialfile=f"{modpack_name}.zip"
            )
            
            if filename:
                modpack_path = os.path.join(MODPACKS_DIR, modpack_name)
                
                if os.path.exists(modpack_path):
                    # Создаем архив
                    shutil.make_archive(filename.replace('.zip', ''), 'zip', modpack_path)
                    self.log(f"Модпак '{modpack_name}' экспортирован в {filename}")
                    messagebox.showinfo("Успех", f"Модпак успешно экспортирован!")
                    
        except Exception as e:
            self.log(f"Ошибка при экспорте модпака: {str(e)}")
            messagebox.showerror("Ошибка", f"Не удалось экспортировать модпак: {str(e)}")
    
    def on_modpack_selected(self, event):
        """Обработчик выбора модпака"""
        try:
            selection = self.modpacks_tree.selection()
            if not selection:
                return
            
            item = self.modpacks_tree.item(selection[0])
            modpack_name = item['values'][0]
            
            # Читаем информацию о модпаке
            info_file = os.path.join(MODPACKS_DIR, modpack_name, "modpack_info.json")
            
            if os.path.exists(info_file):
                with open(info_file, 'r', encoding='utf-8') as f:
                    info = json.load(f)
                
                # Отображаем информацию
                info_text = f"📦 Модпак: {info.get('name', modpack_name)}\n\n"
                info_text += f"📝 Описание: {info.get('description', 'Нет описания')}\n"
                info_text += f"🎮 Версия Minecraft: {info.get('minecraft_version', 'Не указана')}\n"
                info_text += f"🔧 Модлоадер: {info.get('modloader', 'Не указан')}\n"
                info_text += f"📅 Создан: {info.get('created', 'Не указана')}\n"
                
                # Количество модов
                mods_dir = os.path.join(MODPACKS_DIR, modpack_name, "mods")
                mod_count = 0
                if os.path.exists(mods_dir):
                    mod_count = len([f for f in os.listdir(mods_dir) if f.endswith('.jar')])
                
                info_text += f"📦 Количество модов: {mod_count}\n"
                
                self.modpack_info_text.delete(1.0, tk.END)
                self.modpack_info_text.insert(1.0, info_text)
                
                # Устанавливаем как текущий модпак
                self.current_modpack = modpack_name
                self.current_modpack_label.config(text=f"Текущий модпак: {modpack_name}")
                self.refresh_mods_list()
            
        except Exception as e:
            self.log(f"Ошибка при получении информации о модпаке: {str(e)}")

if __name__ == "__main__":
    root = tk.Tk()
    launcher = MinecraftLauncher(root)
    root.mainloop()