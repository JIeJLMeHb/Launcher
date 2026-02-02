import os
import shutil
import json
from datetime import datetime

class SkinManager:
    def __init__(self, launcher):
        self.launcher = launcher
        self.MINECRAFT_DIR = launcher.MINECRAFT_DIR
        self.SKINS_SYNC_DIR = launcher.SKINS_SYNC_DIR
        
    def log(self, message):
        """Логирование через лаунчер"""
        if hasattr(self.launcher, 'log'):
            self.launcher.log(message)
        else:
            print(f"[SkinManager] {message}")
    
    def setup_custom_skin_loader(self):
        """Настройка Custom Skin Loader"""
        try:
            config_dir = os.path.join(self.MINECRAFT_DIR, "CustomSkinLoader")
            os.makedirs(config_dir, exist_ok=True)
            
            config_path = os.path.join(config_dir, "CustomSkinLoader.json")
            
            # Важно: путь должен быть относительно папки .minecraft
            config = {
                "version": "14.27",
                "buildNumber": 37,
                "loadlist": [
                    {
                        "name": "GameProfile",
                        "type": "GameProfile"
                    },
                    {
                        "name": "LocalSkin",
                        "type": "Legacy",
                        "checkPNG": False,
                        "skin": "LocalSkin/skins/{USERNAME}.png",
                        "model": "auto",
                        "cape": "LocalSkin/capes/{USERNAME}.png"
                    },
                    {
                        "name": "Mojang",
                        "type": "MojangAPI",
                        "apiRoot": "https://api.mojang.com/",
                        "sessionRoot": "https://sessionserver.mojang.com/"
                    },
                    {
                        "name": "ElyBy",
                        "type": "ElyByAPI",
                        "root": "http://skinsystem.ely.by/textures/"
                    },
                    {
                        "name": "TLauncher",
                        "type": "ElyByAPI",
                        "root": "https://auth.tlauncher.org/skin/profile/texture/login/"
                    },
                    {
                        "name": "MinecraftCapes",
                        "type": "MinecraftCapesAPI",
                        "root": "https://api.minecraftcapes.net/profile/"
                    },
                    {
                        "name": "OptiFine",
                        "type": "Legacy",
                        "checkPNG": False,
                        "model": "auto",
                        "cape": "https://optifine.net/capes/{USERNAME}.png"
                    }
                ],
                "enableDynamicSkull": True,
                "enableTransparentSkin": True,
                "forceLoadAllTextures": True,
                "enableCape": True,
                "threadPoolSize": 8,
                "enableLogStdOut": True,
                "cacheExpiry": 30,
                "forceUpdateSkull": True,
                "enableLocalProfileCache": False,
                "enableCacheAutoClean": True,
                "forceDisableCache": True
            }
            
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            
            self.log(f"✅ Конфиг CSL создан: {config_path}")
            self.log(f"📁 Путь к скинам в конфиге: LocalSkin/skins/")
            
            # Создаем папку для скинов
            local_skins_dir = os.path.join(self.MINECRAFT_DIR, "CustomSkinLoader", "LocalSkin", "skins")
            os.makedirs(local_skins_dir, exist_ok=True)
            
            # Проверяем, что папка существует
            if os.path.exists(local_skins_dir):
                files = os.listdir(local_skins_dir)
                self.log(f"📁 Файлов в папке LocalSkin/skins: {len(files)}")
                for f in files[:5]:  # Покажем первые 5 файлов
                    self.log(f"  - {f}")
            else:
                self.log("⚠️ Папка LocalSkin/skins не найдена!")
            
            return True
            
        except Exception as e:
            self.log(f"❌ Ошибка настройки CSL: {str(e)}")
            return False
    
    def prepare_local_skins_for_csl(self):
        """Подготовка локальных скинов для Custom Skin Loader"""
        try:
            sync_dir = self.SKINS_SYNC_DIR
            if not os.path.exists(sync_dir):
                self.log("⚠️ Папка синхронизации скинов не найдена")
                return False
            
            # Путь для скинов Custom Skin Loader
            csl_dir = os.path.join(self.MINECRAFT_DIR, "CustomSkinLoader", "LocalSkin", "skins")
            os.makedirs(csl_dir, exist_ok=True)
            
            # Также создаем папку для плащей
            capes_dir = os.path.join(self.MINECRAFT_DIR, "CustomSkinLoader", "LocalSkin", "capes")
            os.makedirs(capes_dir, exist_ok=True)
            
            skin_files = [f for f in os.listdir(sync_dir) if f.endswith('.png')]
            self.log(f"Найдено {len(skin_files)} скинов в папке синхронизации")
            
            copied_count = 0
            for skin_file in skin_files:
                src = os.path.join(sync_dir, skin_file)
                username = os.path.splitext(skin_file)[0]
                
                # Копируем скин с расширением .png
                dst_with_ext = os.path.join(csl_dir, skin_file)
                shutil.copy2(src, dst_with_ext)
                
                # Также копируем без расширения для совместимости с Legacy форматом
                dst_no_ext = os.path.join(csl_dir, username)
                shutil.copy2(src, dst_no_ext)
                
                copied_count += 1
                self.log(f"Подготовлен скин для: {username}")
            
            self.log(f"✅ Подготовлено {copied_count} скинов в {csl_dir}")
            
            # Покажем содержимое папки для отладки
            self.debug_skins_folder(csl_dir)
            
            return True
            
        except Exception as e:
            self.log(f"❌ Ошибка подготовки локальных скинов: {str(e)}")
            import traceback
            self.log(f"Детали: {traceback.format_exc()}")
            return False
    
    def sync_skins_for_local_use(self):
        """Создание локальных копий скинов (для использования в игре)"""
        try:
            # Теперь используем правильный путь для CSL
            skins_dir = os.path.join(self.MINECRAFT_DIR, "CustomSkinLoader", "LocalSkin", "skins")
            os.makedirs(skins_dir, exist_ok=True)
            
            for skin_file in os.listdir(self.SKINS_SYNC_DIR):
                if skin_file.endswith('.png'):
                    src = os.path.join(self.SKINS_SYNC_DIR, skin_file)
                    dst = os.path.join(skins_dir, skin_file)
                    shutil.copy2(src, dst)
            
            self.log(f"✅ Локальные скины подготовлены: {skins_dir}")
            return True
            
        except Exception as e:
            self.log(f"⚠️ Ошибка подготовки локальных скинов: {str(e)}")
            return False
    
    def debug_skins_folder(self, skins_dir):
        """Отладочная информация о папке скинов"""
        try:
            if not os.path.exists(skins_dir):
                self.log(f"❌ Папка {skins_dir} не существует!")
                return
            
            files = os.listdir(skins_dir)
            self.log(f"📁 Содержимое папки LocalSkin/skins ({len(files)} файлов):")
            
            for filename in files:
                filepath = os.path.join(skins_dir, filename)
                if os.path.isfile(filepath):
                    size = os.path.getsize(filepath)
                    self.log(f"  - {filename} ({size} байт)")
                else:
                    self.log(f"  - {filename} [папка]")
                    
        except Exception as e:
            self.log(f"Ошибка при отладке папки скинов: {str(e)}")
    
    def test_csl_local_config(self):
        """Тестирование локальной конфигурации CSL"""
        try:
            config_dir = os.path.join(self.MINECRAFT_DIR, "CustomSkinLoader")
            config_path = os.path.join(config_dir, "CustomSkinLoader.json")
            
            if not os.path.exists(config_path):
                self.log("❌ Конфиг CSL не найден")
                return False
            
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            self.log("=== ТЕСТ КОНФИГА CSL ===")
            
            # Проверяем loadlist
            loadlist = config.get('loadlist', [])
            for loader in loadlist:
                if loader.get('name') == 'LocalSkin':
                    self.log(f"✅ Найден загрузчик LocalSkin")
                    self.log(f"   Тип: {loader.get('type')}")
                    self.log(f"   Путь к скину: {loader.get('skin')}")
                    self.log(f"   Путь к плащу: {loader.get('cape')}")
            
            # Проверяем папку скинов
            skins_dir = os.path.join(self.MINECRAFT_DIR, "CustomSkinLoader", "LocalSkin", "skins")
            if os.path.exists(skins_dir):
                # Ищем скин для тестового пользователя
                test_users = ["JIeJLMeHb", "TestUser", "Player"]
                for username in test_users:
                    # Проверяем файл без расширения (Legacy формат)
                    skin_path_no_ext = os.path.join(skins_dir, username)
                    # Проверяем файл с расширением
                    skin_path_with_ext = os.path.join(skins_dir, f"{username}.png")
                    
                    if os.path.exists(skin_path_no_ext):
                        size = os.path.getsize(skin_path_no_ext)
                        self.log(f"✅ Скин '{username}' найден (без расширения, {size} байт)")
                    elif os.path.exists(skin_path_with_ext):
                        size = os.path.getsize(skin_path_with_ext)
                        self.log(f"✅ Скин '{username}' найден (с расширением .png, {size} байт)")
                    else:
                        self.log(f"❌ Скин для '{username}' не найден")
            else:
                self.log(f"❌ Папка LocalSkin/skins не существует: {skins_dir}")
            
            self.log("=== КОНЕЦ ТЕСТА ===")
            return True
            
        except Exception as e:
            self.log(f"❌ Ошибка тестирования CSL: {str(e)}")
            return False