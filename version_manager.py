import os
import shutil
import subprocess
import threading
import tempfile
import json
import socket
import requests
import minecraft_launcher_lib as mclib
from tkinter import messagebox
from pathlib import Path

class VersionManager:
    def __init__(self, launcher):
        self.launcher = launcher
        self.modloader_versions = {
            "Forge": [],
            "NeoForge": [],
            "Fabric": [],
            "Quilt": []
        }
        self.is_loading_modloader_versions = False
        # Директория для кэша списков версий
        self.cache_dir = os.path.join(launcher.MINECRAFT_DIR, "launcher_cache")
        os.makedirs(self.cache_dir, exist_ok=True)
        self.neoforge_cache_file = os.path.join(self.cache_dir, "neoforge_versions.json")

    def log(self, message):
        """Логирование через лаунчер"""
        self.launcher.log(message)

    def is_connected(self, host="8.8.8.8", port=53, timeout=3):
        """Проверка доступа в интернет (пытаемся подключиться к DNS Google)"""
        try:
            socket.setdefaulttimeout(timeout)
            socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
            return True
        except socket.error:
            return False

    def refresh_versions(self):
        """Обновление списка версий"""
        if hasattr(self.launcher.main_tab, 'refresh_button'):
            self.launcher.main_tab.refresh_button.config(state="disabled")
        self.launcher.main_tab.set_status("Загрузка списка версий...")
        threading.Thread(target=self.load_versions, daemon=True).start()

    def load_versions(self):
        """Загрузка списка версий Minecraft (с поддержкой офлайн)"""
        try:
            if self.is_connected():
                self.log("Есть подключение к интернету, загружаем свежий список версий...")
                version_data = mclib.utils.get_version_list()
                release_versions = [v['id'] for v in version_data if v['type'] == 'release']
            else:
                self.log("Нет подключения к интернету. Загружаем список установленных версий...")
                # Получаем уже установленные версии
                installed = mclib.utils.get_installed_versions(self.launcher.MINECRAFT_DIR)
                release_versions = sorted(set(v['id'] for v in installed), reverse=True)
                if not release_versions:
                    release_versions = ["1.20.4", "1.20.1"]  # заглушка, если совсем ничего нет

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
            # В крайнем случае показываем установленные или тестовые
            try:
                installed = mclib.utils.get_installed_versions(self.launcher.MINECRAFT_DIR)
                fallback = [v['id'] for v in installed]
            except:
                fallback = ["1.20.4", "1.20.1", "1.19.4"]
            self.launcher.root.after(0, self.update_version_combobox, fallback)

    def update_version_combobox(self, versions):
        """Обновление выпадающего списка версий"""
        if hasattr(self.launcher.main_tab, 'version_combobox'):
            self.launcher.main_tab.version_combobox['values'] = versions
            if versions:
                self.launcher.main_tab.version_combobox.set(versions[0])

        self.log(f"Загружено {len(versions)} версий Minecraft")
        self.launcher.main_tab.set_status(f"Загружено {len(versions)} версий")

        if hasattr(self.launcher.main_tab, 'refresh_button'):
            self.launcher.root.after(0, lambda: self.launcher.main_tab.refresh_button.config(state="normal"))

    def on_version_changed(self, event=None):
        """Обработчик изменения версии Minecraft"""
        minecraft_version = self.launcher.main_tab.version_var.get()
        modloader = self.launcher.main_tab.modloader_var.get()

        if minecraft_version and modloader != "Vanilla":
            self.load_modloader_versions(minecraft_version, modloader)

    def on_modloader_changed(self, event=None):
        """Обработчик изменения модлоадера"""
        minecraft_version = self.launcher.main_tab.version_var.get()
        modloader = self.launcher.main_tab.modloader_var.get()

        if minecraft_version and modloader != "Vanilla":
            self.load_modloader_versions(minecraft_version, modloader)
        else:
            self.launcher.root.after(0, self.update_modloader_version_combobox, [])

    def load_modloader_versions(self, minecraft_version, modloader):
        """Загрузка списка версий модлоадера для выбранной версии Minecraft"""
        if self.is_loading_modloader_versions:
            return

        self.is_loading_modloader_versions = True
        threading.Thread(target=self._load_modloader_versions_thread,
                        args=(minecraft_version, modloader),
                        daemon=True).start()

    def _load_modloader_versions_thread(self, minecraft_version, modloader):
        """Поток загрузки версий модлоадера (с кэшированием и офлайн-режимом)"""
        try:
            self.log(f"Загрузка версий {modloader} для Minecraft {minecraft_version}...")
            versions = []

            if modloader == "Forge":
                try:
                    if self.is_connected():
                        forge_versions = mclib.forge.list_forge_versions()
                    else:
                        # В офлайн пытаемся найти установленные Forge версии
                        installed = mclib.utils.get_installed_versions(self.launcher.MINECRAFT_DIR)
                        forge_versions = [v['id'] for v in installed if 'forge' in v['id'].lower()]
                    # Фильтруем
                    versions = [v for v in forge_versions if v.startswith(minecraft_version + "-") or minecraft_version in v]
                    def forge_key(v):
                        try:
                            build = v.split('-')[-1]
                            return [int(p) for p in build.split('.')]
                        except:
                            return [0,0,0]
                    versions.sort(key=forge_key, reverse=True)
                except Exception as e:
                    self.log(f"Ошибка загрузки Forge: {str(e)}")
                    versions = []

            elif modloader == "Fabric":
                try:
                    if self.is_connected():
                        fabric_versions = mclib.fabric.get_all_minecraft_versions()
                    else:
                        # В офлайн смотрим установленные Fabric
                        installed = mclib.utils.get_installed_versions(self.launcher.MINECRAFT_DIR)
                        fabric_versions = [v['id'] for v in installed if 'fabric' in v['id'].lower()]
                    if minecraft_version in fabric_versions:
                        versions = [f"Fabric для {minecraft_version}"]
                    else:
                        # Пытаемся подобрать ближайшую
                        for v in fabric_versions:
                            if v.startswith(minecraft_version.split('.')[0]):
                                versions = [f"Fabric для {v}"]
                                break
                except Exception as e:
                    self.log(f"Ошибка загрузки Fabric: {str(e)}")
                    versions = []

            elif modloader == "NeoForge":
                versions = self._get_neoforge_versions(minecraft_version)

            elif modloader == "Quilt":
                # Пока заглушка
                versions = [f"Quilt для {minecraft_version}"] if self.is_connected() else []

            # Обновляем интерфейс
            self.launcher.root.after(0, self.update_modloader_version_combobox, versions)

            if versions:
                self.log(f"Загружено {len(versions)} версий {modloader}")
            else:
                self.log(f"Версии {modloader} для {minecraft_version} не найдены")

        except Exception as e:
            self.log(f"Ошибка при загрузке версий модлоадера: {str(e)}")
            self.launcher.root.after(0, self.update_modloader_version_combobox, [])
        finally:
            self.is_loading_modloader_versions = False

    def _get_neoforge_versions(self, minecraft_version):
        """Получение списка версий NeoForge для указанной версии Minecraft (с кэшированием)"""
        versions = []
        # Сначала пробуем загрузить из кэша
        if os.path.exists(self.neoforge_cache_file):
            try:
                with open(self.neoforge_cache_file, 'r', encoding='utf-8') as f:
                    cache = json.load(f)
                if minecraft_version in cache:
                    versions = cache[minecraft_version]
                    self.log(f"Загружены версии NeoForge для {minecraft_version} из кэша")
            except Exception as e:
                self.log(f"Ошибка чтения кэша NeoForge: {e}")

        # Если есть интернет, обновляем кэш (даже если уже есть, чтобы получить новые версии)
        if self.is_connected():
            try:
                self.log("Загружаем свежий список NeoForge с Maven...")
                # Используем Maven metadata для получения списка всех версий neoforge
                # Формат: https://maven.neoforged.net/releases/net/neoforged/forge/maven-metadata.xml
                # Но проще получить JSON через API (если есть) или спарсить.
                # В данном примере используем простой подход: получаем HTML страницы со списком версий
                # и извлекаем те, что соответствуют minecraft_version.
                # Более надёжно: использовать Maven Metadata API.
                url = "https://maven.neoforged.net/releases/net/neoforged/forge/"
                response = requests.get(url, timeout=10)
                response.raise_for_status()
                # Парсим HTML (грубо)
                import re
                # Ищем ссылки вида <a href="1.20.1-47.1.0/"> или подобные
                pattern = re.compile(r'<a href="([^"]+)/">')
                all_links = pattern.findall(response.text)
                # Фильтруем только те, которые начинаются с minecraft_version + "-"
                neo_versions = [link for link in all_links if link.startswith(minecraft_version + "-")]
                # Сортируем
                def ver_key(v):
                    try:
                        build = v.split('-')[-1]
                        return [int(x) for x in build.split('.')]
                    except:
                        return [0,0,0]
                neo_versions.sort(key=ver_key, reverse=True)

                # Обновляем кэш
                cache = {}
                if os.path.exists(self.neoforge_cache_file):
                    with open(self.neoforge_cache_file, 'r') as f:
                        cache = json.load(f)
                cache[minecraft_version] = neo_versions
                with open(self.neoforge_cache_file, 'w') as f:
                    json.dump(cache, f, indent=2)

                versions = neo_versions
                self.log(f"Загружено {len(versions)} версий NeoForge из сети")
            except Exception as e:
                self.log(f"Ошибка загрузки NeoForge из сети: {e}")
                # Если не удалось загрузить из сети, оставляем то, что было из кэша
        else:
            self.log("Нет интернета, используем кэшированные версии NeoForge")

        # Если кэш пуст и нет интернета, попробуем показать уже установленные версии NeoForge
        if not versions:
            try:
                installed = mclib.utils.get_installed_versions(self.launcher.MINECRAFT_DIR)
                for ver in installed:
                    vid = ver['id'].lower()
                    if ('neoforge' in vid or 'neoformed' in vid) and minecraft_version in vid:
                        # Извлекаем полную версию (например, "1.20.1-47.1.0")
                        versions.append(ver['id'])
                versions = sorted(set(versions), reverse=True)
                self.log(f"Найдены установленные версии NeoForge: {versions}")
            except Exception as e:
                self.log(f"Ошибка при поиске установленных NeoForge: {e}")

        return versions

    def update_modloader_version_combobox(self, versions):
        """Обновление выпадающего списка версий модлоадера"""
        if hasattr(self.launcher.main_tab, 'modloader_version_combobox'):
            self.launcher.main_tab.modloader_version_combobox['values'] = versions
            if versions:
                self.launcher.main_tab.modloader_version_var.set(versions[0])
            else:
                self.launcher.main_tab.modloader_version_var.set("")

    def install_version(self):
        """Установка выбранной версии Minecraft"""
        minecraft_version = self.launcher.main_tab.version_var.get()
        modloader = self.launcher.main_tab.modloader_var.get()
        modloader_version = self.launcher.main_tab.modloader_version_var.get()

        if not minecraft_version:
            self.log("Ошибка: Выберите версию Minecraft!")
            messagebox.showwarning("Внимание", "Выберите версию Minecraft!")
            return

        if modloader != "Vanilla" and not modloader_version:
            self.log(f"Ошибка: Выберите версию {modloader}!")
            messagebox.showwarning("Внимание", f"Выберите версию {modloader}!")
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
        """Проверка установлена ли версия (работает офлайн)"""
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
                    vid = version['id'].lower()
                    if modloader.lower() == "neoforge":
                        if ("neoforge" in vid or "neoformed" in vid) and minecraft_version in version['id']:
                            return True
                    else:
                        if modloader.lower() in vid and minecraft_version in version['id']:
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
                if modloader_version:
                    mclib.forge.install_forge_version(modloader_version,
                                                     self.launcher.MINECRAFT_DIR,
                                                     callback=callback)
                    self.log(f"Forge {modloader_version} успешно установлен!")
                else:
                    self.log(f"Ошибка: не указана версия Forge")

            elif modloader == "Fabric":
                if not self.is_version_installed(minecraft_version, "Fabric"):
                    fabric_mc_version = minecraft_version
                    if " для " in modloader_version:
                        fabric_mc_version = modloader_version.split(" для ")[1]
                    mclib.fabric.install_fabric(fabric_mc_version,
                                               self.launcher.MINECRAFT_DIR,
                                               callback=callback)
                    self.log(f"Fabric для Minecraft {fabric_mc_version} успешно установлен!")
                else:
                    self.log(f"Fabric для Minecraft {minecraft_version} уже установлен")

            elif modloader == "NeoForge":
                if not self.is_version_installed(minecraft_version, "NeoForge"):
                    self._install_neoforge(minecraft_version, modloader_version, callback)
                else:
                    self.log(f"NeoForge для Minecraft {minecraft_version} уже установлен")

            elif modloader == "Quilt":
                self.log(f"Установка Quilt пока не реализована")
                messagebox.showinfo("Внимание", "Установка Quilt пока не реализована")

            self.log(f"{modloader} установка завершена")

        except Exception as e:
            self.log(f"Ошибка при установке {modloader}: {str(e)}")
            raise

    def _install_neoforge(self, minecraft_version, neoforge_full_version, callback):
        """Установка NeoForge через официальный установщик (скачивание + запуск)"""
        try:
            self.log(f"Начало установки NeoForge {neoforge_full_version}")

            # Формируем URL для скачивания установщика
            # Пример: https://maven.neoforged.net/releases/net/neoforged/forge/1.20.1-47.1.0/forge-1.20.1-47.1.0-installer.jar
            installer_url = (f"https://maven.neoforged.net/releases/net/neoforged/forge/"
                             f"{neoforge_full_version}/forge-{neoforge_full_version}-installer.jar")

            with tempfile.TemporaryDirectory() as temp_dir:
                installer_path = os.path.join(temp_dir, f"neoforge-installer-{neoforge_full_version}.jar")

                # Скачиваем установщик
                self.launcher.main_tab.set_status(f"Скачивание установщика NeoForge...")
                self.log(f"Скачивание {installer_url}")
                response = requests.get(installer_url, stream=True)
                response.raise_for_status()

                with open(installer_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)

                self.log("Установщик NeoForge успешно скачан")

                # Запускаем установщик в тихом режиме
                self.launcher.main_tab.set_status(f"Запуск установщика NeoForge...")
                self.log("Запуск процесса установки NeoForge")

                install_command = [
                    "java",  # предполагается, что Java в PATH
                    "-jar",
                    installer_path,
                    "--installClient",
                    self.launcher.MINECRAFT_DIR
                ]

                process = subprocess.Popen(
                    install_command,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    universal_newlines=True,
                    bufsize=1,
                    encoding='utf-8',
                    errors='replace'
                )

                for line in process.stdout:
                    if line.strip():
                        self.log(f"[NeoForge Installer] {line.strip()}")

                process.wait()

                if process.returncode != 0:
                    raise Exception(f"Установщик NeoForge завершился с ошибкой (код {process.returncode})")

                self.log(f"NeoForge {neoforge_full_version} успешно установлен!")

        except requests.exceptions.RequestException as e:
            self.log(f"Ошибка при скачивании установщика NeoForge: {str(e)}")
            messagebox.showerror("Ошибка", f"Не удалось скачать установщик NeoForge:\n{e}")
            raise
        except subprocess.SubprocessError as e:
            self.log(f"Ошибка при запуске установщика NeoForge: {str(e)}. Убедитесь, что Java установлена и доступна в PATH.")
            messagebox.showerror("Ошибка", "Не удалось запустить установщик NeoForge. Проверьте наличие Java.")
            raise
        except Exception as e:
            self.log(f"Неизвестная ошибка при установке NeoForge: {str(e)}")
            messagebox.showerror("Ошибка", f"Ошибка установки NeoForge:\n{e}")
            raise

    def launch_minecraft(self):
        """Запуск Minecraft"""
        minecraft_version = self.launcher.main_tab.version_var.get()
        modloader = self.launcher.main_tab.modloader_var.get()

        if not minecraft_version:
            self.log("Ошибка: Выберите версию Minecraft!")
            messagebox.showwarning("Внимание", "Выберите версию Minecraft!")
            return

        if modloader != "Vanilla":
            modloader_version = self.launcher.main_tab.modloader_version_var.get()
            if not modloader_version:
                self.log(f"Ошибка: Выберите версию {modloader}!")
                messagebox.showwarning("Внимание", f"Выберите версию {modloader}!")
                return

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

            self.launcher.setup_skin_loader(minecraft_version, modloader)
            self.launcher.sync_skins_for_local_use()

            installed_versions = mclib.utils.get_installed_versions(self.launcher.MINECRAFT_DIR)
            launch_version = minecraft_version

            if modloader == "Forge":
                for v in installed_versions:
                    if "forge" in v['id'].lower() and minecraft_version in v['id']:
                        launch_version = v['id']
                        break
            elif modloader == "Fabric":
                for v in installed_versions:
                    if "fabric" in v['id'].lower():
                        launch_version = v['id']
                        break
            elif modloader == "NeoForge":
                for v in installed_versions:
                    vid = v['id'].lower()
                    if ("neoforge" in vid or "neoformed" in vid) and minecraft_version in v['id']:
                        launch_version = v['id']
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