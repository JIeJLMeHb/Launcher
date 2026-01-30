import os
import shutil
import subprocess
import threading
import tempfile
import minecraft_launcher_lib as mclib
from tkinter import messagebox
from utils import InsecureSession

class VersionManager:
    def __init__(self, launcher):
        self.launcher = launcher
        self.modloader_versions = {
            "Forge": [],
            "NeoForge": [],
            "Fabric": [],
            "Quilt": []
        }
    
    def refresh_versions(self):
        self.launcher.main_tab.refresh_button.config(state="disabled")
        self.launcher.main_tab.set_status("Загрузка списка версий...")
        threading.Thread(target=self.load_versions, daemon=True).start()
    
    def load_versions(self):
        try:
            self.launcher.main_tab.log("Получение списка версий Minecraft...")
            
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
                except Exception:
                    continue
            
            if not version_data:
                raise Exception("Не удалось загрузить список версий")
            
            release_versions = [v['id'] for v in version_data['versions'] if v['type'] == 'release']
            
            def version_key(ver):
                parts = ver.split('.')
                try:
                    return [int(part) for part in parts]
                except ValueError:
                    return [0, 0, 0]
            
            release_versions.sort(key=version_key, reverse=True)
            
            self.launcher.root.after(0, self.update_version_combobox, release_versions)
            self.load_modloader_versions()
            
        except Exception as e:
            self.launcher.main_tab.log(f"Ошибка при загрузке версий: {str(e)}")
            test_versions = ["1.20.4", "1.20.1", "1.19.4", "1.18.2", "1.17.1", "1.16.5"]
            self.launcher.root.after(0, self.update_version_combobox, test_versions)
            self.launcher.main_tab.set_status("Ошибка загрузки версий, используется локальный список")
    
    def load_modloader_versions(self):
        try:
            session = InsecureSession()
            
            self.launcher.main_tab.log("Загрузка версий Forge...")
            forge_versions = mclib.forge.list_forge_versions()
            self.modloader_versions["Forge"] = forge_versions
            
            self.launcher.main_tab.log("Загрузка версий NeoForge...")
            try:
                neoforge_response = session.get("https://maven.neoforged.net/api/maven/versions/releases/net/neoforged/neoforge")
                if neoforge_response.status_code == 200:
                    neoforge_data = neoforge_response.json()
                    self.modloader_versions["NeoForge"] = neoforge_data.get("versions", [])
            except Exception:
                pass
            
            self.launcher.main_tab.log("Загрузка версий Fabric...")
            try:
                fabric_response = session.get("https://meta.fabricmc.net/v2/versions/loader")
                if fabric_response.status_code == 200:
                    fabric_data = fabric_response.json()
                    fabric_versions = []
                    for item in fabric_data:
                        if isinstance(item, dict) and 'loader' in item:
                            fabric_versions.append(item['loader']['version'])
                    self.modloader_versions["Fabric"] = fabric_versions[:50]
            except Exception:
                pass
            
            self.launcher.main_tab.log("Загрузка версий модлоадеров завершена")
            
        except Exception as e:
            self.launcher.main_tab.log(f"Ошибка при загрузке версий модлоадеров: {str(e)}")
    
    def update_version_combobox(self, versions):
        self.launcher.main_tab.version_combobox['values'] = versions
        if versions:
            self.launcher.main_tab.version_combobox.set(versions[0])
        self.launcher.main_tab.log(f"Загружено {len(versions)} версий Minecraft")
        self.launcher.main_tab.set_status(f"Загружено {len(versions)} версий")
        self.launcher.main_tab.refresh_button.config(state="normal")
    
    def install_version(self):
        minecraft_version = self.launcher.main_tab.version_var.get()
        modloader = self.launcher.main_tab.modloader_var.get()
        modloader_version = self.launcher.main_tab.modloader_version_var.get()
        
        if not minecraft_version:
            self.launcher.main_tab.log("Ошибка: Выберите версию Minecraft!")
            messagebox.showwarning("Внимание", "Выберите версию Minecraft!")
            return
        
        self.launcher.main_tab.install_button.config(state="disabled")
        self.launcher.main_tab.launch_button.config(state="disabled")
        
        threading.Thread(target=self._install_version_thread, 
                        args=(minecraft_version, modloader, modloader_version), 
                        daemon=True).start()
    
    def _install_version_thread(self, minecraft_version, modloader, modloader_version):
        try:
            self.launcher.main_tab.set_status(f"Установка Minecraft {minecraft_version}...")
            self.launcher.main_tab.log(f"Начинаем установку Minecraft {minecraft_version}")
            
            os.makedirs(self.launcher.MINECRAFT_DIR, exist_ok=True)
            
            callback = {
                'setStatus': lambda text: self.launcher.root.after(0, self.launcher.main_tab.set_status, text),
                'setMax': lambda max_value: None
            }
            
            if not self.is_version_installed(minecraft_version, "Vanilla"):
                mclib.install.install_minecraft_version(minecraft_version, self.launcher.MINECRAFT_DIR, callback=callback)
                self.launcher.main_tab.log(f"Minecraft {minecraft_version} успешно установлен!")
            else:
                self.launcher.main_tab.log(f"Minecraft {minecraft_version} уже установлен")
            
            if modloader != "Vanilla":
                self.install_modloader(minecraft_version, modloader, modloader_version, callback)
            
            self.launcher.main_tab.set_status(f"Установка завершена")
            
        except Exception as e:
            self.launcher.main_tab.log(f"Ошибка при установке: {str(e)}")
            self.launcher.main_tab.set_status("Ошибка установки")
        finally:
            if self.launcher.root.winfo_exists():
                self.launcher.root.after(0, lambda: self.launcher.main_tab.install_button.config(state="normal"))
                self.launcher.root.after(0, lambda: self.launcher.main_tab.launch_button.config(state="normal"))
    
    def is_version_installed(self, minecraft_version, modloader):
        try:
            installed_versions = mclib.utils.get_installed_versions(self.launcher.MINECRAFT_DIR)
            
            if modloader == "Vanilla":
                for version in installed_versions:
                    if version['id'] == minecraft_version:
                        version_dir = os.path.join(self.launcher.MINECRAFT_DIR, "versions", minecraft_version)
                        jar_file = os.path.join(version_dir, f"{minecraft_version}.jar")
                        return os.path.exists(jar_file)
                return False
            else:
                for version in installed_versions:
                    if modloader.lower() in version['id'].lower() and minecraft_version in version['id']:
                        return True
                return False
        except Exception:
            return False
    
    def install_modloader(self, minecraft_version, modloader, modloader_version, callback):
        try:
            self.launcher.main_tab.set_status(f"Установка {modloader}...")
            self.launcher.main_tab.log(f"Установка {modloader} {modloader_version} для Minecraft {minecraft_version}")
            
            if modloader == "Forge":
                if modloader_version == "Автоматический выбор":
                    for version in self.modloader_versions.get("Forge", []):
                        if version.startswith(minecraft_version):
                            modloader_version = version
                            break
                
                if modloader_version:
                    self.install_forge_with_fallback(minecraft_version, modloader_version, callback)
            
            elif modloader == "Fabric":
                try:
                    if not self.is_version_installed(minecraft_version, "Fabric"):
                        mclib.fabric.install_fabric(minecraft_version, self.launcher.MINECRAFT_DIR, callback=callback)
                        self.launcher.main_tab.log(f"Fabric для Minecraft {minecraft_version} успешно установлен!")
                    else:
                        self.launcher.main_tab.log(f"Fabric для Minecraft {minecraft_version} уже установлен")
                except Exception as e:
                    self.launcher.main_tab.log(f"Ошибка установки Fabric: {str(e)}")
            
            elif modloader == "NeoForge":
                self.launcher.main_tab.log("NeoForge установка требует ручной настройки")
                self.launcher.main_tab.log("Пожалуйста, установите NeoForge вручную")
            
            elif modloader == "Quilt":
                self.launcher.main_tab.log("Quilt установка требует ручной настройки")
                self.launcher.main_tab.log("Пожалуйста, установите Quilt вручную")
            
            self.launcher.main_tab.log(f"{modloader} установка завершена")
            
        except Exception as e:
            self.launcher.main_tab.log(f"Ошибка при установке {modloader}: {str(e)}")
            raise
    
    def install_forge_with_fallback(self, minecraft_version, forge_version, callback):
        try:
            self.launcher.main_tab.log(f"Попытка установки Forge {forge_version} стандартным методом...")
            mclib.forge.install_forge_version(forge_version, self.launcher.MINECRAFT_DIR, callback=callback)
            self.launcher.main_tab.log(f"Forge {forge_version} успешно установлен!")
            
        except Exception as e:
            self.launcher.main_tab.log(f"Ошибка при стандартной установке Forge: {str(e)}")
            self.launcher.main_tab.log("Пробуем альтернативный метод установки...")
            
            try:
                self.install_forge_via_installer(minecraft_version, forge_version, callback)
            except Exception as e2:
                self.launcher.main_tab.log(f"Ошибка при альтернативной установке Forge: {str(e2)}")
                self.launcher.main_tab.log("Пробуем метод прямой загрузки...")
                
                try:
                    self.install_forge_direct_download(minecraft_version, forge_version, callback)
                except Exception as e3:
                    self.launcher.main_tab.log(f"Все методы установки Forge не удались: {str(e3)}")
                    raise Exception(f"Не удалось установить Forge {forge_version}. Попробуйте установить вручную.")
    
    def install_forge_via_installer(self, minecraft_version, forge_version, callback):
        try:
            forge_installer_url = f"https://files.minecraftforge.net/maven/net/minecraftforge/forge/{forge_version}/forge-{forge_version}-installer.jar"
            
            self.launcher.main_tab.set_status(f"Скачивание Forge installer...")
            self.launcher.main_tab.log(f"Скачивание Forge installer с {forge_installer_url}")
            
            temp_dir = tempfile.gettempdir()
            installer_path = os.path.join(temp_dir, f"forge-{forge_version}-installer.jar")
            
            session = InsecureSession()
            response = session.get(forge_installer_url, stream=True, timeout=60)
            
            if response.status_code != 200:
                raise Exception(f"Не удалось скачать Forge installer. Код ответа: {response.status_code}")
            
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            
            with open(installer_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
            
            self.launcher.main_tab.log(f"Forge installer скачан: {installer_path}")
            
            self.launcher.main_tab.set_status("Запуск Forge installer...")
            
            java_path = self.find_java()
            if not java_path:
                raise Exception("Java не найдена")
            
            command = [
                java_path,
                "-jar",
                installer_path,
                "--installClient",
                self.launcher.MINECRAFT_DIR
            ]
            
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                encoding='utf-8'
            )
            
            for line in process.stdout:
                if line.strip():
                    self.launcher.main_tab.log(f"Forge installer: {line.strip()}")
            
            process.wait()
            os.remove(installer_path)
            
            self.launcher.main_tab.log("Forge установлен через installer")
            
        except Exception as e:
            self.launcher.main_tab.log(f"Ошибка при установке через installer: {str(e)}")
            raise
    
    def install_forge_direct_download(self, minecraft_version, forge_version, callback):
        try:
            self.launcher.main_tab.set_status("Прямая загрузка Forge через библиотеку...")
            self.launcher.main_tab.log(f"Используем minecraft_launcher_lib для установки Forge {forge_version}")

            # Пробуем установить с помощью встроенной функции
            mclib.forge.install_forge_version(forge_version, self.launcher.MINECRAFT_DIR, callback=callback)

            self.launcher.main_tab.log("Forge успешно установлен через minecraft_launcher_lib")
        except Exception as e:
            self.launcher.main_tab.log(f"Критическая ошибка при установке Forge: {str(e)}")
            # Предложите пользователю установить Forge вручную
            self.launcher.root.after(0, lambda: messagebox.showerror(
                "Ошибка установки",
                f"Автоматическая установка Forge не удалась.\n\n"
                f"Пожалуйста, установите Forge {forge_version} вручную:\n"
                f"1. Скачайте установщик с https://files.minecraftforge.net\n"
                f"2. Выберите 'Install client' и укажите папку '{self.launcher.MINECRAFT_DIR}'\n"
                f"3. После этого попробуйте запустить игру снова."
            ))
            raise Exception(f"Не удалось установить Forge автоматически: {str(e)}")
    
    def find_java(self):
        java_home = os.environ.get('JAVA_HOME')
        if java_home:
            java_path = os.path.join(java_home, 'bin', 'java.exe')
            if os.path.exists(java_path):
                return java_path
        
        possible_paths = [
            r'C:\Program Files\Java\jre-1.8\bin\java.exe',
            r'C:\Program Files\Java\jdk-1.8\bin\java.exe',
            r'C:\Program Files\Java\jre1.8.0_XXX\bin\java.exe',
            r'C:\Program Files (x86)\Java\jre1.8.0_XXX\bin\java.exe',
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                return path
        
        try:
            result = subprocess.run(['where', 'java'], capture_output=True, text=True)
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip().split('\n')[0]
        except Exception:
            pass
        
        return None
    
    def launch_minecraft(self):
        minecraft_version = self.launcher.main_tab.version_var.get()
        modloader = self.launcher.main_tab.modloader_var.get()
        
        if not minecraft_version:
            self.launcher.main_tab.log("Ошибка: Выберите версию Minecraft!")
            messagebox.showwarning("Внимание", "Выберите версию Minecraft!")
            return
        
        username = self.launcher.main_tab.username_entry.get().strip()
        uuid = self.launcher.main_tab.uuid_entry.get().strip()
        token = self.launcher.main_tab.token_entry.get().strip()
        
        if not username:
            self.launcher.main_tab.log("Ошибка: Введите имя пользователя!")
            messagebox.showwarning("Внимание", "Введите имя пользователя!")
            return
        
        if not self.is_version_installed(minecraft_version, modloader):
            self.launcher.main_tab.log(f"Версия {minecraft_version} не установлена. Начинаем установку...")
            if messagebox.askyesno("Установка", 
                                 f"Версия Minecraft {minecraft_version} не установлена.\n"
                                 f"Установить ее сейчас?"):
                self.install_version()
                self.launcher.main_tab.log("После установки нажмите 'Запуск Minecraft' снова.")
            return
        
        self.launcher.main_tab.log(f"Запуск Minecraft {minecraft_version} с {modloader} для пользователя: {username}")
        
        self.launcher.main_tab.launch_button.config(state="disabled")
        self.launcher.main_tab.install_button.config(state="disabled")
        
        threading.Thread(target=self._launch_minecraft_thread, 
                        args=(minecraft_version, modloader, username, uuid, token), 
                        daemon=True).start()
    
    def _launch_minecraft_thread(self, minecraft_version, modloader, username, uuid, token):
        try:
            self.launcher.main_tab.set_status("Подготовка к запуску...")
                        # НАСТРОЙКА SKIN LOADER ПЕРЕД ЗАПУСКОМ
            self.launcher.main_tab.log("Настройка отображения скинов...")
            
            # 1. Проверяем и настраиваем Custom Skin Loader
            self.launcher.setup_skin_loader(minecraft_version, modloader)
            
            # 2. Создаем локальную копию всех скинов для офлайн-доступа
            self.launcher.sync_skins_for_local_use()
            
            launch_version = minecraft_version
            if modloader == "Forge":
                installed_versions = mclib.utils.get_installed_versions(self.launcher.MINECRAFT_DIR)
                for version in installed_versions:
                    if "forge" in version['id'].lower() and minecraft_version in version['id']:
                        launch_version = version['id']
                        break
                else:
                    for version in installed_versions:
                        if "forge" in version['id'].lower():
                            launch_version = version['id']
                            self.launcher.main_tab.log(f"Используется найденная Forge версия: {launch_version}")
                            break
            
            elif modloader == "Fabric":
                installed_versions = mclib.utils.get_installed_versions(self.launcher.MINECRAFT_DIR)
                for version in installed_versions:
                    if "fabric" in version['id'].lower():
                        launch_version = version['id']
                        break
            
            version_dir = os.path.join(self.launcher.MINECRAFT_DIR, "versions", launch_version)
            if not os.path.exists(version_dir):
                self.launcher.main_tab.log(f"Ошибка: Папка версии {launch_version} не найдена!")
                self.launcher.root.after(0, lambda: messagebox.showerror("Ошибка", 
                    f"Папка версии {launch_version} не найдена!\n"
                    f"Попробуйте установить версию заново."))
                return
            
            jar_files = [f for f in os.listdir(version_dir) if f.endswith('.jar')]
            if not jar_files:
                self.launcher.main_tab.log(f"Ошибка: В папке версии {launch_version} нет JAR файлов!")
                self.launcher.root.after(0, lambda: messagebox.showerror("Ошибка",
                    f"В папке версии {launch_version} нет JAR файлов!\n"
                    f"Попробуйте установить версию заново."))
                return
            
            options = {
                "username": username,
                "uuid": uuid if uuid else "",
                "token": token if token else "",
                "jvmArguments": ["-Xmx16G", "-Xms2G", "-XX:+UseG1GC", "-XX:+UnlockExperimentalVMOptions", "-XX:G1NewSizePercent=20", "-XX:G1ReservePercent=20", "-XX:MaxGCPauseMillis=50", "-XX:G1HeapRegionSize=32M"]
            }
            
            if self.launcher.current_modpack:
                modpack_mods_dir = os.path.join(self.launcher.MODPACKS_DIR, self.launcher.current_modpack, "mods")
                if os.path.exists(modpack_mods_dir):
                    working_mods_dir = os.path.join(self.launcher.MINECRAFT_DIR, "mods")
                    os.makedirs(working_mods_dir, exist_ok=True)
                    
                    for file in os.listdir(working_mods_dir):
                        if file.endswith('.jar'):
                            os.remove(os.path.join(working_mods_dir, file))
                    
                    for file in os.listdir(modpack_mods_dir):
                        if file.endswith('.jar'):
                            shutil.copy2(os.path.join(modpack_mods_dir, file), 
                                       os.path.join(working_mods_dir, file))
            
            options["gameDirectory"] = self.launcher.MINECRAFT_DIR
            
            self.launcher.main_tab.log(f"Используется версия: {launch_version}")
            self.launcher.main_tab.log("Генерация команды запуска...")
            
            try:
                minecraft_command = mclib.command.get_minecraft_command(launch_version, self.launcher.MINECRAFT_DIR, options)
            except Exception as e:
                self.launcher.main_tab.log(f"Ошибка при генерации команды: {str(e)}")
                self.launcher.root.after(0, lambda: messagebox.showerror("Ошибка",
                    f"Не удалось сгенерировать команду запуска для версии {launch_version}.\n"
                    f"Версия может быть повреждена. Попробуйте переустановить."))
                return
            
            cmd_preview = ' '.join(minecraft_command[:3]) + '...' if len(minecraft_command) > 3 else ' '.join(minecraft_command)
            self.launcher.main_tab.log(f"Команда запуска: {cmd_preview}")
            
            self.launcher.main_tab.log("Запуск Minecraft...")
            self.launcher.main_tab.set_status("Minecraft запускается...")
            
            process = subprocess.Popen(
                minecraft_command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1,
                encoding='utf-8',
                errors='replace'
            )
            
            for line in process.stdout:
                if line.strip():
                    self.launcher.main_tab.log(f"> {line.strip()}")
            
            process.wait()
            self.launcher.main_tab.log("Игра завершена.")
            self.launcher.main_tab.set_status("Готов к работе")
            
        except Exception as e:
            self.launcher.main_tab.log(f"Произошла ошибка при запуске: {str(e)}")
            self.launcher.main_tab.set_status("Ошибка запуска")
            
            if "Invalid paths argument" in str(e) and modloader == "Forge":
                self.launcher.root.after(0, self.handle_forge_library_error, minecraft_version, modloader)
            else:
                self.launcher.root.after(0, lambda: messagebox.showerror("Ошибка запуска",
                    f"Не удалось запустить Minecraft:\n{str(e)}\n\n"
                    f"Проверьте:\n"
                    f"1. Установлена ли версия {minecraft_version}\n"
                    f"2. Наличие Java 8 или выше\n"
                    f"3. Правильность пути к .minecraft\n"
                    f"4. Целостность установленных файлов"))
        finally:
            if self.launcher.root.winfo_exists():
                self.launcher.root.after(0, lambda: self.launcher.main_tab.launch_button.config(state="normal"))
                self.launcher.root.after(0, lambda: self.launcher.main_tab.install_button.config(state="normal"))
    
    def handle_forge_library_error(self, minecraft_version, modloader):
        response = messagebox.askyesno("Ошибка библиотек Forge",
                                      f"Не удалось запустить Forge для версии {minecraft_version}.\n"
                                      f"Возможно, некоторые библиотеки отсутствуют или повреждены.\n\n"
                                      f"Хотите попробовать переустановить Forge?")
        
        if response:
            modloader_version = self.launcher.main_tab.modloader_version_var.get()
            if modloader_version == "Автоматический выбор":
                for version in self.modloader_versions.get("Forge", []):
                    if version.startswith(minecraft_version):
                        modloader_version = version
                        break
            
            if modloader_version:
                self.launcher.main_tab.log(f"Начинаем переустановку Forge {modloader_version}...")
                threading.Thread(target=self.reinstall_forge, 
                               args=(minecraft_version, modloader_version), 
                               daemon=True).start()
    
    def reinstall_forge(self, minecraft_version, forge_version):
        try:
            self.launcher.main_tab.set_status(f"Переустановка Forge {forge_version}...")
            self.launcher.main_tab.log(f"Начинаем переустановку Forge {forge_version}")
            
            self.remove_forge_files(minecraft_version, forge_version)
            
            callback = {
                'setStatus': lambda text: self.launcher.root.after(0, self.launcher.main_tab.set_status, text),
                'setMax': lambda max_value: None
            }
            
            self.install_forge_with_fallback(minecraft_version, forge_version, callback)
            
            self.launcher.main_tab.log(f"Forge {forge_version} переустановлен успешно!")
            self.launcher.main_tab.set_status("Переустановка завершена")
            
            messagebox.showinfo("Успех", f"Forge {forge_version} был успешно переустановлен.\nТеперь можно попробовать запустить игру снова.")
            
        except Exception as e:
            self.launcher.main_tab.log(f"Ошибка при переустановке Forge: {str(e)}")
            messagebox.showerror("Ошибка", f"Не удалось переустановить Forge: {str(e)}")
    
    def remove_forge_files(self, minecraft_version, forge_version):
        try:
            self.launcher.main_tab.log("Удаление старых файлов Forge...")
            
            forge_version_dir = os.path.join(self.launcher.MINECRAFT_DIR, "versions", f"{minecraft_version}-forge-{forge_version.split('-')[-1]}")
            if os.path.exists(forge_version_dir):
                shutil.rmtree(forge_version_dir)
                self.launcher.main_tab.log(f"Удалена папка версии: {forge_version_dir}")
            
            forge_lib_dir = os.path.join(self.launcher.MINECRAFT_DIR, "libraries", "net", "minecraftforge", "forge", forge_version)
            if os.path.exists(forge_lib_dir):
                shutil.rmtree(forge_lib_dir)
                self.launcher.main_tab.log(f"Удалены библиотеки Forge: {forge_lib_dir}")
            
            self.launcher.main_tab.log("Старые файлы Forge удалены")
            
        except Exception as e:
            self.launcher.main_tab.log(f"Ошибка при удалении файлов Forge: {str(e)}")
            raise