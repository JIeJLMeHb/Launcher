import requests
import json
import os
import hashlib
from typing import Dict, List, Optional
from tkinter import messagebox
import time

class APIClient:
    def __init__(self, launcher):
        self.launcher = launcher
        self.base_url = "https://JIeJLMeHb.pythonanywhere.com"
        self.api_key = ""
        self.username = ""
        self.config_file = "api_config.json"
        self.load_config()

    def _log(self, message):
        """Безопасное логирование - работает даже если main_tab еще не создан"""
        try:
            # Пробуем использовать main_tab если он доступен
            if hasattr(self.launcher, 'main_tab') and self.launcher.main_tab is not None:
                self.launcher.main_tab.log(message)
            else:
                # Иначе выводим в консоль
                print(f"[APIClient] {message}")
                # Сохраняем сообщения для последующего вывода
                if not hasattr(self, '_pending_logs'):
                    self._pending_logs = []
                self._pending_logs.append(message)
        except Exception:
            print(f"[APIClient] {message}")

    def _flush_pending_logs(self):
        """Выводит накопленные логи в main_tab когда он станет доступен"""
        if hasattr(self, '_pending_logs') and self._pending_logs:
            if hasattr(self.launcher, 'main_tab') and self.launcher.main_tab is not None:
                for msg in self._pending_logs:
                    self.launcher.main_tab.log(f"[Отложено] {msg}")
                self._pending_logs.clear()

    def load_config(self):
        """Загружает конфигурацию"""
        try:
            if not os.path.exists(self.config_file):
                self._log("Конфигурационный файл не найден, создаю шаблон...")
                self.create_template_config()
                return
            
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # Загружаем данные с проверкой
            self.api_key = config.get('api_key', '')
            self.username = config.get('username', '')
            
            # Безопасно получаем base_url
            new_base_url = config.get('base_url', '')
            if new_base_url and new_base_url != self.base_url:
                self.base_url = new_base_url
                self._log(f"URL сервера обновлен: {self.base_url}")
            
            self._log(f"Конфигурация загружена. Пользователь: {self.username if self.username else 'Не указан'}")
            
        except json.JSONDecodeError:
            self._log("Ошибка в формате JSON, создаю новый конфиг")
            self.create_template_config()
        except Exception as e:
            self._log(f"Ошибка загрузки конфигурации: {str(e)}")

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
            self._log(f"✅ Создан шаблонный конфиг: {self.config_file}")
        except Exception as e:
            self._log(f"❌ Ошибка создания конфига: {str(e)}")

    def save_config(self):
        """Сохраняет текущую конфигурацию в файл"""
        try:
            config = {
                'api_key': self.api_key,
                'username': self.username,
                'base_url': self.base_url
            }
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=2)
            self._log("Конфигурация API сохранена")
        except Exception as e:
            self._log(f"Ошибка сохранения конфигурации: {str(e)}")
    
    def register_user(self, username, password):
        """Регистрация нового пользователя"""
        try:
            # Проверяем параметры
            if not username or not password:
                self._log("❌ Имя пользователя и пароль не могут быть пустыми")
                return False
            
            # Параметры передаются в query string
            response = requests.post(
                f"{self.base_url}/api/auth/register",
                params={"username": username, "password": password},
                timeout=10
            )
            
            self._log(f"[DEBUG] Регистрация: статус={response.status_code}, ответ={response.text}")
            
            if response.status_code == 200:
                data = response.json()
                self.api_key = data['api_key']
                self.username = username
                self.save_config()
                self._log(f"✅ Пользователь {username} зарегистрирован")
                return True
            
            # Пробуем получить детальную ошибку
            try:
                error_data = response.json()
                error_msg = error_data.get('detail', response.text)
            except:
                error_msg = response.text
            
            self._log(f"❌ Ошибка регистрации: {error_msg}")
            return False
            
        except Exception as e:
            self._log(f"❌ Исключение при регистрации: {str(e)}")
            return False

    def login_user(self, username, password):
        """Вход пользователя"""
        try:
            # Проверяем параметры
            if not username or not password:
                self._log("❌ Имя пользователя и пароль не могут быть пустыми")
                return False
            
            response = requests.post(
                f"{self.base_url}/api/auth/login",
                params={"username": username, "password": password},
                timeout=10
            )
            
            self._log(f"[DEBUG] Вход: статус={response.status_code}, ответ={response.text}")
            
            if response.status_code == 200:
                data = response.json()
                self.api_key = data['api_key']
                self.username = username
                self.save_config()
                self._log(f"✅ Пользователь {username} вошел в систему")
                return True
            
            # Пробуем получить детальную ошибку
            try:
                error_data = response.json()
                error_msg = error_data.get('detail', response.text)
            except:
                error_msg = response.text
            
            self._log(f"❌ Ошибка входа: {error_msg}")
            return False
            
        except Exception as e:
            self._log(f"❌ Исключение при входе: {str(e)}")
            return False
    
    def upload_skin(self, skin_path, username=None):
        """Загружает скин на сервер"""
        try:
            # Проверяем авторизацию
            if not self.api_key:
                self._log("❌ Необходимо сначала войти или зарегистрироваться")
                return False
            
            # Определяем имя пользователя
            if not username:
                username = self.username
            
            if not username:
                self._log("❌ Имя пользователя не указано")
                return False
            
            # Проверяем файл
            if not os.path.exists(skin_path):
                self._log(f"❌ Файл скина не найден: {skin_path}")
                return False
            
            # Проверяем расширение файла
            allowed_extensions = ['.png', '.jpg', '.jpeg']
            file_ext = os.path.splitext(skin_path)[1].lower()
            if file_ext not in allowed_extensions:
                self._log(f"❌ Неподдерживаемый формат файла: {file_ext}. Используйте: {', '.join(allowed_extensions)}")
                return False
            
            file_size = os.path.getsize(skin_path)
            self._log(f"🔄 Начинаю загрузку скина для пользователя {username}...")
            self._log(f"📁 Файл: {skin_path} (размер: {file_size} байт)")
            
            # Открываем файл
            with open(skin_path, 'rb') as f:
                files = {'file': (os.path.basename(skin_path), f, f'image/{file_ext[1:]}')}
                headers = {'Authorization': f'Bearer {self.api_key}'}
                
                # Отладочная информация
                self._log(f"[DEBUG] URL: {self.base_url}/api/skins/upload?username={username}")
                self._log(f"[DEBUG] Используемый API ключ: {self.api_key[:10]}...")
                
                # Отправляем запрос
                response = requests.post(
                    f"{self.base_url}/api/skins/upload?username={username}",
                    files=files,
                    headers=headers,
                    timeout=30
                )
            
            # Анализируем ответ
            self._log(f"[DEBUG] Status Code: {response.status_code}")
            self._log(f"[DEBUG] Response Text: {response.text}")
            
            if response.status_code == 200:
                result = response.json()
                self._log(f"✅ Скин загружен успешно! URL: {result.get('url', 'N/A')}")
                return True
            elif response.status_code == 401:
                self._log("❌ Неверный API ключ. Войдите заново")
                self.api_key = ""  # Сбрасываем ключ
                self.save_config()
                return False
            elif response.status_code == 400:
                # Ошибка валидации файла
                try:
                    error_data = response.json()
                    error_msg = error_data.get('detail', 'Unknown error')
                except:
                    error_msg = response.text
                self._log(f"❌ Ошибка файла: {error_msg}")
                return False
            else:
                self._log(f"❌ Ошибка сервера ({response.status_code}): {response.text}")
                return False
                
        except requests.exceptions.ConnectionError:
            self._log("❌ Нет подключения к серверу")
            return False
        except Exception as e:
            self._log(f"❌ Исключение при загрузке: {str(e)}")
            return False

    def get_skins_manifest(self):
        """Получает манифест всех скинов с сервера"""
        try:
            self._log(f"📋 Запрашиваю манифест скинов с {self.base_url}/api/skins/manifest")
            
            # Пробуем получить манифест
            response = requests.get(
                f"{self.base_url}/api/skins/manifest",
                timeout=10
            )
            
            self._log(f"[DEBUG] Манифест: статус={response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                skins_count = len(data.get('skins', {}))
                self._log(f"✅ Получен манифест скинов, всего: {skins_count}")
                
                # Если манифест пустой, пробуем получить упрощенный список
                if skins_count == 0:
                    self._log("⚠️ Манифест пустой, пробую получить упрощенный список...")
                    return self._get_simple_skins_list()
                
                return data
                
            elif response.status_code == 404:
                self._log("⚠️ Манифест не найден (404), пробую получить упрощенный список...")
                return self._get_simple_skins_list()
            else:
                self._log(f"❌ Ошибка при получении манифеста скинов: {response.status_code}")
                return self._get_simple_skins_list()
                
        except Exception as e:
            self._log(f"❌ Исключение при получении манифеста скинов: {str(e)}")
            return self._get_simple_skins_list()

    def _get_simple_skins_list(self):
        """Получает упрощенный список скинов"""
        try:
            self._log("📋 Запрашиваю упрощенный список скинов")
            response = requests.get(
                f"{self.base_url}/api/skins/list",
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                skins_list = data.get('skins', [])
                skins_count = len(skins_list)
                
                # Преобразуем список в формат манифеста
                manifest = {"skins": {}}
                for skin in skins_list:
                    username = skin.get('username')
                    if username:
                        manifest["skins"][username] = {
                            "filename": skin.get('filename'),
                            "size": skin.get('size'),
                            "url": skin.get('url'),
                            "updated_at": skin.get('modified'),
                            "extension": os.path.splitext(skin.get('filename', ''))[1].lower()
                        }
                
                self._log(f"✅ Получен упрощенный список скинов, всего: {skins_count}")
                return manifest
            else:
                self._log(f"❌ Не удалось получить упрощенный список: {response.status_code}")
                return {"skins": {}}
                
        except Exception as e:
            self._log(f"❌ Исключение при получении упрощенного списка: {str(e)}")
            return {"skins": {}}

    def download_skin(self, username, dest_path):
        """Скачивает скин по имени пользователя"""
        try:
            self._log(f"⬇️  Скачиваю скин для пользователя {username}")
            
            # Вариант 1: Пробуем через API эндпоинт
            try:
                response = requests.get(
                    f"{self.base_url}/api/skins/{username}",
                    timeout=10
                )
                
                self._log(f"[DEBUG] API эндпоинт: статус={response.status_code}")
                
                if response.status_code == 200:
                    # Убедимся, что директория существует
                    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                    
                    # Сохраняем файл
                    with open(dest_path, 'wb') as f:
                        f.write(response.content)
                    
                    # Проверяем, что файл не пустой
                    file_size = os.path.getsize(dest_path)
                    if file_size > 0:
                        self._log(f"✅ Скин для {username} скачан через API ({file_size} байт)")
                        return True
                    else:
                        self._log(f"⚠️  Файл скина пуст, пробую альтернативный метод")
                        os.remove(dest_path)  # Удаляем пустой файл
                else:
                    self._log(f"⚠️  API эндпоинт вернул {response.status_code}, пробую альтернативный метод")
            except Exception as e:
                self._log(f"⚠️  Ошибка API эндпоинта: {str(e)}, пробую альтернативный метод")
            
            # Вариант 2: Пробуем через манифест и статический URL
            manifest = self.get_skins_manifest()
            if manifest and username in manifest.get('skins', {}):
                skin_info = manifest['skins'][username]
                filename = skin_info.get('filename', f"{username}.png")
                
                # Пробуем скачать через статический URL
                static_url = f"{self.base_url}/uploads/skins/{filename}"
                self._log(f"🔄 Пробую скачать скин через статический URL: {static_url}")
                
                response = requests.get(static_url, timeout=10)
                if response.status_code == 200:
                    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                    with open(dest_path, 'wb') as f:
                        f.write(response.content)
                    
                    file_size = os.path.getsize(dest_path)
                    if file_size > 0:
                        self._log(f"✅ Скин для {username} скачан через статику ({file_size} байт)")
                        return True
            
            # Если оба метода не сработали
            self._log(f"❌ Скин для {username} не найден на сервере")
            return False
            
        except Exception as e:
            self._log(f"❌ Исключение при скачивании скина {username}: {str(e)}")
            return False

    def get_available_skins(self):
        """Получить список всех скинов на сервере"""
        try:
            self._log("📋 Запрашиваю список всех скинов")
            response = requests.get(
                f"{self.base_url}/api/skins",
                timeout=10
            )
            
            self._log(f"[DEBUG] Список скинов: статус={response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                skins = data.get('skins', [])
                self._log(f"✅ Получен список скинов, всего: {len(skins)}")
                return skins
            else:
                self._log(f"❌ Ошибка получения списка скинов: {response.status_code}")
                return []
                
        except Exception as e:
            self._log(f"❌ Исключение при получении списка скинов: {str(e)}")
            return []

    def test_connection(self):
        """Проверяет соединение с сервером"""
        try:
            self._log(f"🔗 Проверяю соединение с {self.base_url}")
            response = requests.get(
                f"{self.base_url}/api/health",
                timeout=5
            )
            
            self._log(f"[DEBUG] Проверка соединения: статус={response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                self._log(f"✅ Сервер доступен: {data.get('status', 'OK')}")
                return True
            else:
                self._log(f"⚠️ Сервер ответил с кодом: {response.status_code}")
                return False
                
        except requests.exceptions.ConnectionError:
            self._log("❌ Не удалось подключиться к серверу")
            return False
        except Exception as e:
            self._log(f"❌ Ошибка при проверке соединения: {str(e)}")
            return False

    def get_server_stats(self):
        """Получает статистику сервера"""
        try:
            self._log("📊 Запрашиваю статистику сервера")
            response = requests.get(
                f"{self.base_url}/api/stats",
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                self._log(f"✅ Получена статистика сервера")
                return data.get('stats', {})
            else:
                self._log(f"❌ Ошибка получения статистики: {response.status_code}")
                return None
                
        except Exception as e:
            self._log(f"❌ Исключение при получении статистики: {str(e)}")
            return None

    def delete_skin(self, username=None):
        """Удаляет скин пользователя с сервера"""
        try:
            if not self.api_key:
                self._log("❌ Необходима авторизация")
                return False
            
            if not username:
                username = self.username
            
            if not username:
                self._log("❌ Имя пользователя не указано")
                return False
            
            self._log(f"🗑️  Пытаюсь удалить скин для пользователя {username}")
            
            headers = {'Authorization': f'Bearer {self.api_key}'}
            response = requests.delete(
                f"{self.base_url}/api/skins/{username}",
                headers=headers,
                timeout=10
            )
            
            self._log(f"[DEBUG] Удаление скина: статус={response.status_code}, ответ={response.text}")
            
            if response.status_code == 200:
                self._log(f"✅ Скин для {username} удален")
                return True
            elif response.status_code == 404:
                self._log(f"⚠️ Скин для {username} не найден")
                return False
            elif response.status_code == 403:
                self._log("❌ Нет прав для удаления")
                return False
            else:
                self._log(f"❌ Ошибка при удалении: {response.status_code}")
                return False
                
        except Exception as e:
            self._log(f"❌ Исключение при удалении скина: {str(e)}")
            return False

    def get_modpacks_list(self):
        """Получает список модпаков с сервера"""
        try:
            self._log("📦 Запрашиваю список модпаков")
            response = requests.get(
                f"{self.base_url}/api/modpacks",
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                modpacks = data.get('modpacks', [])
                self._log(f"✅ Получен список модпаков, всего: {len(modpacks)}")
                return modpacks
            else:
                self._log(f"❌ Ошибка при получении списка модпаков: {response.status_code}")
                return []
        except Exception as e:
            self._log(f"❌ Исключение при получении списка модпаков: {str(e)}")
            return []

    def download_modpack(self, modpack_id, dest_dir):
        """Скачивает модпак"""
        try:
            self._log(f"⬇️  Скачиваю модпак {modpack_id}")
            
            # Сначала получим информацию о модпаке
            modpacks = self.get_modpacks_list()
            modpack_info = None
            for mp in modpacks:
                if mp.get('id') == modpack_id:
                    modpack_info = mp
                    break
            
            if not modpack_info:
                self._log(f"❌ Модпак {modpack_id} не найден")
                return False
            
            filename = modpack_info.get('filename', f"{modpack_id}.zip")
            url = f"{self.base_url}/uploads/modpacks/{filename}"
            
            self._log(f"📥 Скачиваю модпак из: {url}")
            
            response = requests.get(url, timeout=60, stream=True)
            if response.status_code == 200:
                # Создаем директорию
                os.makedirs(dest_dir, exist_ok=True)
                
                # Сохраняем файл
                dest_path = os.path.join(dest_dir, filename)
                with open(dest_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                
                self._log(f"✅ Модпак {modpack_id} скачан в {dest_path}")
                return True
            else:
                self._log(f"❌ Ошибка при скачивании модпака {modpack_id}: {response.status_code}")
                return False
        except Exception as e:
            self._log(f"❌ Исключение при скачивании модпака {modpack_id}: {str(e)}")
            return False

    def debug_server_files(self):
        """Отладочная функция для проверки файлов на сервере"""
        try:
            self._log("🔍 Запрашиваю отладочную информацию о файлах")
            response = requests.get(
                f"{self.base_url}/api/debug/files",
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                self._log("✅ Получена отладочная информация о файлах")
                return data
            else:
                self._log(f"❌ Ошибка получения отладочной информации: {response.status_code}")
                return None
        except Exception as e:
            self._log(f"❌ Исключение при получении отладочной информации: {str(e)}")
            return None