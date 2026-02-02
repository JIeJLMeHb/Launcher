import requests
import json
import os
from typing import Dict, List, Optional
import time

class APIClient:
    def __init__(self, launcher):
        self.launcher = launcher
        self.base_url = "https://JIeJLMeHb.pythonanywhere.com"
        self.api_key = ""
        self.username = ""
        self.config_file = "api_config.json"
        self.load_config()

    def log(self, message):
        """Унифицированное логирование через лаунчер"""
        if hasattr(self.launcher, 'log'):
            self.launcher.log(message)
        else:
            print(f"[APIClient] {message}")

    def load_config(self):
        """Загружает конфигурацию"""
        try:
            if not os.path.exists(self.config_file):
                self.create_template_config()
                return
            
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            self.api_key = config.get('api_key', '')
            self.username = config.get('username', '')
            
            new_base_url = config.get('base_url', '')
            if new_base_url and new_base_url != self.base_url:
                self.base_url = new_base_url
            
        except json.JSONDecodeError:
            self.create_template_config()
        except Exception as e:
            self.log(f"Ошибка загрузки конфигурации: {str(e)}")

    def create_template_config(self):
        """Создает шаблонный конфигурационный файл"""
        template = {
            "api_key": "",
            "username": "",
            "base_url": "https://JIeJLMeHb.pythonanywhere.com"
        }
        
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(template, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.log(f"Ошибка создания конфига: {str(e)}")

    def save_config(self):
        """Сохраняет текущую конфигурацию в файл"""
        try:
            config = {
                'api_key': self.api_key,
                'username': self.username,
                'base_url': self.base_url
            }
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2)
        except Exception as e:
            self.log(f"Ошибка сохранения конфигурации: {str(e)}")
    
    def register_user(self, username, password):
        """Регистрация нового пользователя"""
        try:
            if not username or not password:
                self.log("Имя пользователя и пароль не могут быть пустыми")
                return False
            
            response = requests.post(
                f"{self.base_url}/api/auth/register",
                params={"username": username, "password": password},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                self.api_key = data['api_key']
                self.username = username
                self.save_config()
                return True
            
            try:
                error_data = response.json()
                error_msg = error_data.get('detail', response.text)
            except:
                error_msg = response.text
            
            self.log(f"Ошибка регистрации: {error_msg}")
            return False
            
        except Exception as e:
            self.log(f"Исключение при регистрации: {str(e)}")
            return False

    def login_user(self, username, password):
        """Вход пользователя"""
        try:
            if not username or not password:
                self.log("Имя пользователя и пароль не могут быть пустыми")
                return False
            
            response = requests.post(
                f"{self.base_url}/api/auth/login",
                params={"username": username, "password": password},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                self.api_key = data['api_key']
                self.username = username
                self.save_config()
                return True
            
            try:
                error_data = response.json()
                error_msg = error_data.get('detail', response.text)
            except:
                error_msg = response.text
            
            self.log(f"Ошибка входа: {error_msg}")
            return False
            
        except Exception as e:
            self.log(f"Исключение при входе: {str(e)}")
            return False
    
    def upload_skin(self, skin_path, username=None):
        """Загружает скин на сервер"""
        try:
            if not self.api_key:
                self.log("Необходимо сначала войти или зарегистрироваться")
                return False
            
            if not username:
                username = self.username
            
            if not username:
                self.log("Имя пользователя не указано")
                return False
            
            if not os.path.exists(skin_path):
                self.log(f"Файл скина не найден: {skin_path}")
                return False
            
            allowed_extensions = ['.png', '.jpg', '.jpeg']
            file_ext = os.path.splitext(skin_path)[1].lower()
            if file_ext not in allowed_extensions:
                self.log(f"Неподдерживаемый формат файла: {file_ext}")
                return False
            
            with open(skin_path, 'rb') as f:
                files = {'file': (os.path.basename(skin_path), f, f'image/{file_ext[1:]}')}
                headers = {'Authorization': f'Bearer {self.api_key}'}
                
                response = requests.post(
                    f"{self.base_url}/api/skins/upload?username={username}",
                    files=files,
                    headers=headers,
                    timeout=30
                )
            
            if response.status_code == 200:
                return True
            elif response.status_code == 401:
                self.log("Неверный API ключ. Войдите заново")
                self.api_key = ""
                self.save_config()
                return False
            elif response.status_code == 400:
                try:
                    error_data = response.json()
                    error_msg = error_data.get('detail', 'Unknown error')
                except:
                    error_msg = response.text
                self.log(f"Ошибка файла: {error_msg}")
                return False
            else:
                self.log(f"Ошибка сервера ({response.status_code}): {response.text}")
                return False
                
        except requests.exceptions.ConnectionError:
            self.log("Нет подключения к серверу")
            return False
        except Exception as e:
            self.log(f"Исключение при загрузке: {str(e)}")
            return False

    def get_skins_manifest(self):
        """Получает манифест всех скинов с сервера"""
        try:
            response = requests.get(
                f"{self.base_url}/api/skins/manifest",
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return {"skins": {}}
                
        except Exception as e:
            self.log(f"Исключение при получении манифеста: {str(e)}")
            return {"skins": {}}

    def download_skin(self, username, dest_path):
        """Скачивает скин по имени пользователя"""
        try:
            # Пробуем через API эндпоинт
            response = requests.get(
                f"{self.base_url}/api/skins/{username}",
                timeout=10
            )
            
            if response.status_code == 200:
                os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                
                with open(dest_path, 'wb') as f:
                    f.write(response.content)
                
                return True
            else:
                # Пробуем через манифест
                manifest = self.get_skins_manifest()
                if manifest and username in manifest.get('skins', {}):
                    skin_info = manifest['skins'][username]
                    filename = skin_info.get('filename', f"{username}.png")
                    
                    static_url = f"{self.base_url}/uploads/skins/{filename}"
                    response = requests.get(static_url, timeout=10)
                    if response.status_code == 200:
                        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                        with open(dest_path, 'wb') as f:
                            f.write(response.content)
                        return True
            
            return False
            
        except Exception as e:
            self.log(f"Исключение при скачивании скина: {str(e)}")
            return False

    def get_available_skins(self):
        """Получить список всех скинов на сервере"""
        try:
            response = requests.get(
                f"{self.base_url}/api/skins",
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get('skins', [])
            else:
                return []
                
        except Exception as e:
            self.log(f"Исключение при получении списка скинов: {str(e)}")
            return []

    def test_connection(self):
        """Проверяет соединение с сервером"""
        try:
            response = requests.get(
                f"{self.base_url}/api/health",
                timeout=5
            )
            
            if response.status_code == 200:
                return True
            else:
                return False
                
        except requests.exceptions.ConnectionError:
            self.log("Не удалось подключиться к серверу")
            return False
        except Exception as e:
            self.log(f"Ошибка при проверке соединения: {str(e)}")
            return False

    def get_server_stats(self):
        """Получает статистику сервера"""
        try:
            response = requests.get(
                f"{self.base_url}/api/stats",
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get('stats', {})
            else:
                return None
                
        except Exception as e:
            self.log(f"Исключение при получении статистики: {str(e)}")
            return None

    def delete_skin(self, username=None):
        """Удаляет скин пользователя с сервера"""
        try:
            if not self.api_key:
                self.log("Необходима авторизация")
                return False
            
            if not username:
                username = self.username
            
            if not username:
                self.log("Имя пользователя не указано")
                return False
            
            headers = {'Authorization': f'Bearer {self.api_key}'}
            response = requests.delete(
                f"{self.base_url}/api/skins/{username}",
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                return True
            elif response.status_code == 404:
                self.log(f"Скин для {username} не найден")
                return False
            elif response.status_code == 403:
                self.log("Нет прав для удаления")
                return False
            else:
                self.log(f"Ошибка при удалении: {response.status_code}")
                return False
                
        except Exception as e:
            self.log(f"Исключение при удалении скина: {str(e)}")
            return False

    def get_modpacks_list(self):
        """Получает список модпаков с сервера"""
        try:
            response = requests.get(
                f"{self.base_url}/api/modpacks",
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get('modpacks', [])
            else:
                return []
        except Exception as e:
            self.log(f"Исключение при получении списка модпаков: {str(e)}")
            return []

    def download_modpack(self, modpack_id, dest_dir):
        """Скачивает модпак"""
        try:
            modpacks = self.get_modpacks_list()
            modpack_info = None
            for mp in modpacks:
                if mp.get('id') == modpack_id:
                    modpack_info = mp
                    break
            
            if not modpack_info:
                self.log(f"Модпак {modpack_id} не найден")
                return False
            
            filename = modpack_info.get('filename', f"{modpack_id}.zip")
            url = f"{self.base_url}/uploads/modpacks/{filename}"
            
            response = requests.get(url, timeout=60, stream=True)
            if response.status_code == 200:
                os.makedirs(dest_dir, exist_ok=True)
                
                dest_path = os.path.join(dest_dir, filename)
                with open(dest_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                
                return True
            else:
                self.log(f"Ошибка при скачивании модпака: {response.status_code}")
                return False
        except Exception as e:
            self.log(f"Исключение при скачивании модпака: {str(e)}")
            return False