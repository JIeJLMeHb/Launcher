import os
import shutil
import json

class SkinManager:
    def __init__(self, launcher):
        self.launcher = launcher
        self.custom_skin_loader_dir = os.path.join(self.launcher.MINECRAFT_DIR, "CustomSkinLoader")
        self.setup_custom_skin_loader()
    
    def setup_custom_skin_loader(self):
        """Настроить Custom Skin Loader"""
        os.makedirs(self.custom_skin_loader_dir, exist_ok=True)
        
        # Конфигурация Custom Skin Loader
        config = {
            "enable": True,
            "loadlist": [
                {
                    "name": "LocalSkins",
                    "type": "Legacy",
                    "root": os.path.relpath(self.launcher.SKINS_SYNC_DIR, self.launcher.MINECRAFT_DIR)
                }
            ]
        }
        
        config_path = os.path.join(self.custom_skin_loader_dir, "CustomSkinLoader.json")
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
        
        self.launcher.main_tab.log("Custom Skin Loader настроен")
    
    def install_skin_loader_mod(self, minecraft_version: str, modloader: str):
        """Установить мод Custom Skin Loader"""
        mod_path = None
        
        if modloader == "Fabric":
            mod_path = self.download_fabric_mod(minecraft_version)
        elif modloader == "Forge":
            mod_path = self.download_forge_mod(minecraft_version)
        
        if mod_path:
            # Копируем мод в папку mods
            dest_dir = os.path.join(self.launcher.MINECRAFT_DIR, "mods")
            os.makedirs(dest_dir, exist_ok=True)
            shutil.copy2(mod_path, os.path.join(dest_dir, os.path.basename(mod_path)))
            self.launcher.main_tab.log("Custom Skin Loader установлен")
    
    def download_fabric_mod(self, version: str) -> str:
        """Скачать Fabric версию мода"""
        # Здесь логика скачивания с Modrinth или CurseForge
        pass
    
    def download_forge_mod(self, version: str) -> str:
        """Скачать Forge версию мода"""
        # Здесь логика скачивания с Modrinth или CurseForge
        pass