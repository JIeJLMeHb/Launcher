import tkinter as tk
from tkinter import ttk
import minecraft_launcher_lib as mclib
import subprocess
import threading
import os
import warnings
import ssl

# ===== SSL FIXES =====
# Глобальное отключение SSL проверки
ssl._create_default_https_context = ssl._create_unverified_context

# Отключаем все предупреждения
warnings.filterwarnings("ignore")

# Устанавливаем переменные окружения для отключения SSL
os.environ['CURL_CA_BUNDLE'] = ''
os.environ['REQUESTS_CA_BUNDLE'] = ''
os.environ['PYTHONHTTPSVERIFY'] = '0'

# Патчим requests и urllib3 для отключения SSL
import requests
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Создаем небезопасную сессию для requests
class InsecureSession(requests.Session):
    def __init__(self):
        super().__init__()
        self.verify = False

# Заменяем стандартные методы requests
requests.Session = InsecureSession

# Патчим minecraft_launcher_lib для использования небезопасных запросов
original_get_requests = mclib._helper.get_requests_response_cache

def insecure_get_requests(url: str):
    session = InsecureSession()
    response = session.get(url)
    response.raise_for_status()
    return response

mclib._helper.get_requests_response_cache = insecure_get_requests

# ===== LAUNCHER CODE =====
MINECRAFT_DIR = ".minecraft"

class MinecraftLauncher:
    def __init__(self, root):
        self.root = root
        self.root.title("Minecraft Launcher")
        self.root.geometry("600x500")
        
        # Основной фрейм
        main_frame = tk.Frame(root)
        main_frame.pack(padx=10, pady=10, fill="both", expand=True)
        
        # Заголовок с предупреждением об SSL
        warning_label = tk.Label(main_frame, text="ВНИМАНИЕ: SSL проверка отключена!", 
                               fg="red", font=("Arial", 10, "bold"))
        warning_label.pack(pady=5)
        
        # Заголовок
        label = tk.Label(main_frame, text="Выберите версию Minecraft", font=("Arial", 12))
        label.pack(pady=10)
        
        # Фрейм для выбора версии
        version_frame = tk.Frame(main_frame)
        version_frame.pack(fill="x", pady=5)
        
        tk.Label(version_frame, text="Версия:").pack(side="left")
        self.version_var = tk.StringVar()
        self.version_combobox = ttk.Combobox(version_frame, textvariable=self.version_var, 
                                           state="readonly", width=30)
        self.version_combobox.pack(side="left", padx=5)
        
        # Кнопка обновления списка версий
        self.refresh_button = tk.Button(version_frame, text="Обновить", command=self.refresh_versions)
        self.refresh_button.pack(side="left", padx=5)
        
        # Фрейм для данных аккаунта
        account_frame = tk.LabelFrame(main_frame, text="Данные аккаунта")
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
        self.progress = ttk.Progressbar(main_frame, mode='determinate')
        self.progress.pack(fill="x", pady=5)
        self.progress_label = tk.Label(main_frame, text="")
        self.progress_label.pack()
        
        # Фрейм для кнопок
        button_frame = tk.Frame(main_frame)
        button_frame.pack(pady=10)
        
        # Кнопка установки
        self.install_button = tk.Button(button_frame, text="Установить версию", 
                                      command=self.install_version,
                                      bg="blue", fg="white")
        self.install_button.pack(side="left", padx=5)
        
        # Кнопка запуска
        self.launch_button = tk.Button(button_frame, text="Запуск Minecraft", 
                                     command=self.launch_minecraft,
                                     bg="green", fg="white", font=("Arial", 10, "bold"))
        self.launch_button.pack(side="left", padx=5)
        
        # Текстовое поле для логов
        log_frame = tk.LabelFrame(main_frame, text="Логи")
        log_frame.pack(fill="both", expand=True, pady=5)
        
        self.log_text = tk.Text(log_frame, height=12)
        scrollbar = tk.Scrollbar(log_frame, command=self.log_text.yview)
        self.log_text.config(yscrollcommand=scrollbar.set)
        
        self.log_text.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        scrollbar.pack(side="right", fill="y")
        
        # Статус бар
        self.status_var = tk.StringVar()
        self.status_var.set("Готов к работе")
        status_bar = tk.Label(main_frame, textvariable=self.status_var, relief="sunken", anchor="w")
        status_bar.pack(fill="x", pady=5)
        
        # Загружаем список версий
        self.refresh_versions()
    
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
            progress_percent = (value / max_value)
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
            
            # Используем нашу небезопасную сессию
            session = InsecureSession()
            response = session.get("https://launchermeta.mojang.com/mc/game/version_manifest_v2.json", timeout=30)
            version_data = response.json()
            
            # Фильтруем только стабильные релизы
            release_versions = [v['id'] for v in version_data['versions'] if v['type'] == 'release']
            
            # Сортируем версии по убыванию (новые версии первыми)
            def version_key(ver):
                parts = ver.split('.')
                try:
                    return [int(part) for part in parts]
                except ValueError:
                    return [0, 0, 0]
            
            release_versions.sort(key=version_key, reverse=True)
            
            self.root.after(0, self.update_version_combobox, release_versions)
            
        except Exception as e:
            self.log(f"Ошибка при загрузке версий: {str(e)}")
            # Локальные версии на случай ошибки
            test_versions = ["1.20.4", "1.20.1", "1.19.4", "1.18.2", "1.17.1", "1.16.5"]
            self.root.after(0, self.update_version_combobox, test_versions)
            self.set_status("Ошибка загрузки версий, используется локальный список")
    
    def update_version_combobox(self, versions):
        """Обновляет комбобокс с версиями"""
        self.version_combobox['values'] = versions
        if versions:
            self.version_combobox.set(versions[0])
        self.log(f"Загружено {len(versions)} версий")
        self.set_status(f"Загружено {len(versions)} версий")
        self.refresh_button.config(state="normal")
    
    def install_version(self):
        """Устанавливает выбранную версию Minecraft"""
        version = self.version_var.get()
        if not version:
            self.log("Ошибка: Выберите версию для установки!")
            return
        
        self.install_button.config(state="disabled")
        self.launch_button.config(state="disabled")
        threading.Thread(target=self._install_version_thread, args=(version,), daemon=True).start()
    
    def _install_version_thread(self, version):
        """Поток для установки версии"""
        try:
            self.set_status(f"Установка версии {version}...")
            self.log(f"Начинаем установку версии {version}")
            
            # Создаем директорию если нет
            os.makedirs(MINECRAFT_DIR, exist_ok=True)
            
            # Создаем правильный callback для отслеживания прогресса
            callback = {
                'setStatus': lambda text: self.root.after(0, self.set_status, text),
                'setProgress': lambda value: self.root.after(0, self.update_progress, value, 100),
                'setMax': lambda max_value: None  # Не используется в нашем случае
            }
            
            # Устанавливаем версию с правильным callback
            mclib.install.install_minecraft_version(version, MINECRAFT_DIR, callback=callback)
            
            self.log(f"Версия {version} успешно установлена!")
            self.set_status(f"Версия {version} установлена")
            self.root.after(0, lambda: self.install_button.config(state="normal"))
            self.root.after(0, lambda: self.launch_button.config(state="normal"))
            
        except Exception as e:
            self.log(f"Ошибка при установке: {str(e)}")
            self.set_status("Ошибка установки")
            self.root.after(0, lambda: self.install_button.config(state="normal"))
            self.root.after(0, lambda: self.launch_button.config(state="normal"))
    
    def launch_minecraft(self):
        """Запускает Minecraft"""
        version = self.version_var.get()
        if not version:
            self.log("Ошибка: Выберите версию!")
            return
        
        # Получаем данные из полей ввода
        username = self.username_entry.get().strip()
        uuid = self.uuid_entry.get().strip()
        token = self.token_entry.get().strip()
        
        if not username:
            self.log("Ошибка: Введите имя пользователя!")
            return
        
        self.log(f"Запуск Minecraft {version} для пользователя: {username}")
        if uuid:
            self.log(f"Используется UUID: {uuid}")
        if token:
            self.log("Используется токен аутентификации")
        
        self.launch_button.config(state="disabled")
        self.install_button.config(state="disabled")
        threading.Thread(target=self._launch_minecraft_thread, args=(version, username, uuid, token), daemon=True).start()
    
    def _launch_minecraft_thread(self, version, username, uuid, token):
        """Поток для запуска Minecraft"""
        try:
            self.set_status("Подготовка к запуску...")
            
            # Проверяем установлена ли версия
            versions_installed = mclib.utils.get_installed_versions(MINECRAFT_DIR)
            version_installed = any(v['id'] == version for v in versions_installed)
            
            if not version_installed:
                self.log(f"Версия {version} не установлена. Начинаем установку...")
                self._install_version_thread(version)
            
            # Подготавливаем опции запуска
            options = {
                "username": username,
                "uuid": uuid,
                "token": token
            }
            
            # Получаем команду для запуска
            self.log("Генерация команды запуска...")
            minecraft_command = mclib.command.get_minecraft_command(version, MINECRAFT_DIR, options)
            
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

if __name__ == "__main__":
    root = tk.Tk()
    launcher = MinecraftLauncher(root)
    root.mainloop()