import os
import shutil
import subprocess
import threading
import tempfile
import minecraft_launcher_lib as mclib
from tkinter import messagebox

class VersionManager:
    def __init__(self, launcher):
        self.launcher = launcher
        self.modloader_versions = {
            "Forge": [],
            "NeoForge": [],
            "Fabric": [],
            "Quilt": []
        }
    
    def log(self, message):
        """Логирование через лаунчер"""
        self.launcher.log(message)
    
    def refresh_versions(self):
        """Обновление списка версий"""
        if hasattr(self.launcher.main_tab, 'refresh_button'):
            self.launcher.main_tab.refresh_button.config(state="disabled")
        self.launcher.main_tab.set_status("Загрузка списка версий...")
        threading.Thread(target=self.load_versions, daemon=True).start()
    
    def load_versions(self):
        """Загрузка списка версий Minecraft"""
        try:
            self.log("Получение списка версий Minecraft...")
            version_data = mclib.utils.get_version_list()
            
            release_versions = [v['id'] for v in version_data if v['type'] == 'release']
            
            def version_key(ver):
                parts = ver.split('.')
                try:
                    return [int(part) for part in parts]
                except ValueError:
                    return [0, 0, 0]
            
            release_versions.sort(key=version_key, reverse=True)
            
            self.launcher.root.after(0, self.update_version_combobox, release_versions[:50])
            
        except Exception as e:
            self.log(f"Ошибка при загрузке версий: {str(e)}")
            test_versions = ["1.20.4", "1.20.1", "1.19.4", "1.18.2", "1.17.1", "1.16.5"]
            self.launcher.root.after(0, self.update_version_combobox, test_versions)
    
    def update_version_combobox(self, versions):
        """Обновление выпадающего списка версий"""
        if hasattr(self.launcher.main_tab, 'version_combobox'):
            self.launcher.main_tab.version_combobox['values'] = versions
            if versions:
                self.launcher.main_tab.version_combobox.set(versions[0])
        
        self.log(f"Загружено {len(versions)} версий Minecraft")
        self.launcher.main_tab.set_status(f"Загружено {len(versions)} версий")
        
        if hasattr(self.launcher.main_tab, 'refresh_button'):
            self.launcher.main_tab.refresh_button.config(state="normal")
    
    def install_version(self):
        """Установка выбранной версии Minecraft"""
        minecraft_version = self.launcher.main_tab.version_var.get()
        modloader = self.launcher.main_tab.modloader_var.get()
        modloader_version = self.launcher.main_tab.modloader_version_var.get()
        
        if not minecraft_version:
            self.log("Ошибка: Выберите версию Minecraft!")
            messagebox.showwarning("Внимание", "Выберите версию Minecraft!")
            return
        
        if hasattr(self.launcher.main_tab, 'install_button'):
            self.launcher.main_tab.install_button.config(state="disabled")
        if hasattr(self.launcher.main_tab, 'launch_button'):
            self.launcher.main_tab.launch_button.config(state="disabled")
        
        threading.Thread(target=self._install_version_thread, 
                        args=(minecraft_version, modloader, modloader_version), 
                        daemon=True).start()
    
    def _install_version_thread(self, minecraft_version, modloader, modloader_version):
        """Поток установки версии"""
        try:
            self.launcher.main_tab.set_status(f"Установка Minecraft {minecraft_version}...")
            self.log(f"Начинаем установку Minecraft {minecraft_version}")
            
            os.makedirs(self.launcher.MINECRAFT_DIR, exist_ok=True)
            
            callback = {
                'setStatus': lambda text: self.launcher.root.after(0, self.launcher.main_tab.set_status, text)
            }
            
            if not self.is_version_installed(minecraft_version, "Vanilla"):
                mclib.install.install_minecraft_version(minecraft_version, 
                                                       self.launcher.MINECRAFT_DIR, 
                                                       callback=callback)
                self.log(f"Minecraft {minecraft_version} успешно установлен!")
            else:
                self.log(f"Minecraft {minecraft_version} уже установлен")
            
            if modloader != "Vanilla":
                self.install_modloader(minecraft_version, modloader, modloader_version, callback)
            
            self.launcher.main_tab.set_status(f"Установка завершена")
            
        except Exception as e:
            self.log(f"Ошибка при установке: {str(e)}")
            self.launcher.main_tab.set_status("Ошибка установки")
        finally:
            if self.launcher.root.winfo_exists():
                if hasattr(self.launcher.main_tab, 'install_button'):
                    self.launcher.root.after(0, lambda: self.launcher.main_tab.install_button.config(state="normal"))
                if hasattr(self.launcher.main_tab, 'launch_button'):
                    self.launcher.root.after(0, lambda: self.launcher.main_tab.launch_button.config(state="normal"))
    
    def is_version_installed(self, minecraft_version, modloader):
        """Проверка установлена ли версия"""
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
        """Установка модлоадера"""
        try:
            self.launcher.main_tab.set_status(f"Установка {modloader}...")
            self.log(f"Установка {modloader} для Minecraft {minecraft_version}")
            
            if modloader == "Forge":
                if modloader_version == "Автоматический выбор":
                    for version in self.modloader_versions.get("Forge", []):
                        if version.startswith(minecraft_version):
                            modloader_version = version
                            break
                
                if modloader_version:
                    mclib.forge.install_forge_version(modloader_version, 
                                                     self.launcher.MINECRAFT_DIR, 
                                                     callback=callback)
            
            elif modloader == "Fabric":
                if not self.is_version_installed(minecraft_version, "Fabric"):
                    mclib.fabric.install_fabric(minecraft_version, 
                                               self.launcher.MINECRAFT_DIR, 
                                               callback=callback)
                    self.log(f"Fabric для Minecraft {minecraft_version} успешно установлен!")
                else:
                    self.log(f"Fabric для Minecraft {minecraft_version} уже установлен")
            
            self.log(f"{modloader} установка завершена")
            
        except Exception as e:
            self.log(f"Ошибка при установке {modloader}: {str(e)}")
    
    def launch_minecraft(self):
        """Запуск Minecraft"""
        minecraft_version = self.launcher.main_tab.version_var.get()
        modloader = self.launcher.main_tab.modloader_var.get()
        
        if not minecraft_version:
            self.log("Ошибка: Выберите версию Minecraft!")
            messagebox.showwarning("Внимание", "Выберите версию Minecraft!")
            return
        
        # Подготавливаем скины для CSL
        self.launcher.prepare_local_skins_for_csl()
        
        username = self.launcher.main_tab.username_entry.get().strip()
        uuid = self.launcher.main_tab.uuid_entry.get().strip()
        token = self.launcher.main_tab.token_entry.get().strip()

        if not username:
            self.log("Ошибка: Введите имя пользователя!")
            messagebox.showwarning("Внимание", "Введите имя пользователя!")
            return
        
        if not self.is_version_installed(minecraft_version, modloader):
            self.log(f"Версия {minecraft_version} не установлена.")
            if messagebox.askyesno("Установка", 
                                 f"Версия Minecraft {minecraft_version} не установлена.\n"
                                 f"Установить ее сейчас?"):
                self.install_version()
                self.log("После установки нажмите 'Запуск Minecraft' снова.")
            return
        
        if hasattr(self.launcher.main_tab, 'launch_button'):
            self.launcher.main_tab.launch_button.config(state="disabled")
        if hasattr(self.launcher.main_tab, 'install_button'):
            self.launcher.main_tab.install_button.config(state="disabled")
        
        threading.Thread(target=self._launch_minecraft_thread, 
                        args=(minecraft_version, modloader, username, uuid, token), 
                        daemon=True).start()
    
    def _launch_minecraft_thread(self, minecraft_version, modloader, username, uuid, token):
        """Поток запуска Minecraft"""
        try:
            self.launcher.main_tab.set_status("Подготовка к запуску...")
            self.log("Настройка отображения скинов...")
            
            # Настраиваем Custom Skin Loader
            self.launcher.setup_skin_loader(minecraft_version, modloader)
            
            # Создаем локальные копии скинов
            self.launcher.sync_skins_for_local_use()
            
            launch_version = minecraft_version
            if modloader == "Forge":
                installed_versions = mclib.utils.get_installed_versions(self.launcher.MINECRAFT_DIR)
                for version in installed_versions:
                    if "forge" in version['id'].lower() and minecraft_version in version['id']:
                        launch_version = version['id']
                        break
            
            elif modloader == "Fabric":
                installed_versions = mclib.utils.get_installed_versions(self.launcher.MINECRAFT_DIR)
                for version in installed_versions:
                    if "fabric" in version['id'].lower():
                        launch_version = version['id']
                        break
            
            options = {
                "username": username,
                "uuid": uuid if uuid else "",
                "token": token if token else "",
                "jvmArguments": ["-Xmx16G", "-Xms10G"],
                "gameDirectory": self.launcher.MINECRAFT_DIR
            }
            
            if self.launcher.current_modpack:
                modpack_mods_dir = os.path.join(self.launcher.MODPACKS_DIR, 
                                              self.launcher.current_modpack, 
                                              "mods")
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
            
            self.log(f"Используется версия: {launch_version}")
            
            try:
                minecraft_command = mclib.command.get_minecraft_command(launch_version, 
                                                                       self.launcher.MINECRAFT_DIR, 
                                                                       options)
            except Exception as e:
                self.log(f"Ошибка при генерации команды: {str(e)}")
                self.launcher.root.after(0, lambda: messagebox.showerror("Ошибка",
                    f"Не удалось сгенерировать команду запуска для версии {launch_version}."))
                return
            
            self.log("Запуск Minecraft...")
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
                    self.log(f"> {line.strip()}")
            
            process.wait()
            self.log("Игра завершена.")
            self.launcher.main_tab.set_status("Готов к работе")
            
        except Exception as e:
            self.log(f"Произошла ошибка при запуске: {str(e)}")
            self.launcher.main_tab.set_status("Ошибка запуска")
            
            self.launcher.root.after(0, lambda: messagebox.showerror("Ошибка запуска",
                f"Не удалось запустить Minecraft:\n{str(e)}"))
        finally:
            if self.launcher.root.winfo_exists():
                if hasattr(self.launcher.main_tab, 'launch_button'):
                    self.launcher.root.after(0, lambda: self.launcher.main_tab.launch_button.config(state="normal"))
                if hasattr(self.launcher.main_tab, 'install_button'):
                    self.launcher.root.after(0, lambda: self.launcher.main_tab.install_button.config(state="normal"))