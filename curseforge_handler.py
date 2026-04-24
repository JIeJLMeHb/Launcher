import os
import json
import shutil
import requests
import zipfile
import threading
from pathlib import Path
from typing import Dict, List, Optional
import re

class CurseForgeHandler:
    def __init__(self, launcher):
        self.launcher = launcher
        self.CURSEFORGE_API = "https://api.curseforge.com/v1"
        self.CURSEFORGE_API_KEY = "YOUR_API_KEY_HERE"  # Get from CurseForge
        self.cache_dir = os.path.join(launcher.MINECRAFT_DIR, "curseforge_cache")
        os.makedirs(self.cache_dir, exist_ok=True)
    
    def log(self, message):
        """Unified logging"""
        if hasattr(self.launcher, 'log'):
            self.launcher.log(message)
        else:
            print(f"[CurseForge] {message}")
    
    def get_modpack_info_from_zip(self, zip_path: str) -> Optional[Dict]:
        """Extract modpack info from CurseForge zip file"""
        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                # Read manifest.json
                if 'manifest.json' not in zip_ref.namelist():
                    self.log("❌ manifest.json not found in archive")
                    return None
                
                manifest_data = zip_ref.read('manifest.json')
                manifest = json.loads(manifest_data.decode('utf-8'))
                
                return manifest
        except Exception as e:
            self.log(f"❌ Error reading modpack info: {str(e)}")
            return None
    
    def extract_modpack_files(self, zip_path: str, modpack_name: str) -> bool:
        """Extract modpack files from zip"""
        try:
            modpack_dir = os.path.join(self.launcher.MODPACKS_DIR, modpack_name)
            os.makedirs(modpack_dir, exist_ok=True)
            
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                # Extract overrides (configs, resourcepacks, etc.)
                for item in zip_ref.namelist():
                    if item.startswith('overrides/'):
                        # Extract file maintaining directory structure
                        extracted_path = os.path.join(modpack_dir, item[10:])  # Remove 'overrides/' prefix
                        
                        if item.endswith('/'):
                            os.makedirs(extracted_path, exist_ok=True)
                        else:
                            os.makedirs(os.path.dirname(extracted_path), exist_ok=True)
                            with zip_ref.open(item) as source, open(extracted_path, 'wb') as target:
                                target.write(source.read())
            
            self.log(f"✅ Modpack files extracted to {modpack_dir}")
            return True
            
        except Exception as e:
            self.log(f"❌ Error extracting modpack: {str(e)}")
            return False
    
    def download_mods_from_manifest(self, manifest: Dict, modpack_name: str) -> bool:
        """Download mods referenced in manifest.json"""
        try:
            mods_dir = os.path.join(self.launcher.MODPACKS_DIR, modpack_name, "mods")
            os.makedirs(mods_dir, exist_ok=True)
            
            files = manifest.get('files', [])
            total_files = len(files)
            
            self.log(f"📦 Starting download of {total_files} mods...")
            
            downloaded = 0
            failed = []
            
            for idx, file_info in enumerate(files, 1):
                file_id = file_info.get('fileID')
                project_id = file_info.get('projectID')
                required = file_info.get('required', True)
                
                if not file_id or not project_id:
                    continue
                
                self.log(f"⏳ Downloading mod {idx}/{total_files}...")
                
                if self._download_curse_mod(project_id, file_id, mods_dir):
                    downloaded += 1
                else:
                    failed.append(f"Project:{project_id} File:{file_id}")
            
            self.log(f"✅ Downloaded {downloaded}/{total_files} mods")
            
            if failed:
                self.log(f"⚠️  Failed to download: {', '.join(failed[:5])}")
            
            return len(failed) < total_files // 2  # Success if majority downloaded
            
        except Exception as e:
            self.log(f"❌ Error downloading mods: {str(e)}")
            return False
    
    def _download_curse_mod(self, project_id: int, file_id: int, dest_dir: str) -> bool:
        """Download a single mod from CurseForge using direct URL"""
        try:
            # Try direct URL format (works for most mods)
            url = f"https://mediafire.com/api/1.5/file/get/file_id={file_id}"
            
            # Alternative: Use the CurseForge API if you have a key
            url = f"{self.CURSEFORGE_API}/mods/{project_id}/files/{file_id}/download-url"
            
            # However, simpler approach: construct the standard CurseForge CDN URL
            # Format: https://media.forgecdn.net/files/{folder1}/{folder2}/{filename}
            
            # Use file info endpoint
            file_url = self._get_curseforge_file_url(project_id, file_id)
            
            if not file_url:
                return False
            
            response = requests.get(file_url, stream=True, timeout=30)
            response.raise_for_status()
            
            # Get filename from response headers or URL
            if 'Content-Disposition' in response.headers:
                filename = response.headers['Content-Disposition'].split('filename=')[-1].strip('"')
            else:
                filename = file_url.split('/')[-1]
            
            if not filename.endswith('.jar'):
                filename += '.jar'
            
            file_path = os.path.join(dest_dir, filename)
            
            # Check if already downloaded
            if os.path.exists(file_path):
                return True
            
            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            return True
            
        except Exception as e:
            self.log(f"⚠️  Failed to download mod {project_id}: {str(e)}")
            return False
    
    def _get_curseforge_file_url(self, project_id: int, file_id: int) -> Optional[str]:
        """Get direct download URL for CurseForge file"""
        try:
            # Method 1: Try CurseForge API if key is available
            if self.CURSEFORGE_API_KEY:
                headers = {'X-Api-Key': self.CURSEFORGE_API_KEY}
                url = f"{self.CURSEFORGE_API}/mods/{project_id}/files/{file_id}"
                response = requests.get(url, headers=headers, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    download_url = data.get('data', {}).get('downloadUrl')
                    if download_url:
                        return download_url
            
            # Method 2: Use ForgeAPI (deprecated but still works)
            # Format: https://mediafire.com/api/1.5/file/{id}
            
            # Method 3: Construct standard CDN URL
            # Convert file ID to folder structure (divide by 1000)
            folder1 = file_id // 1000
            folder2 = file_id % 1000
            
            # Try common patterns
            patterns = [
                f"https://edge.forgecdn.net/files/{folder1}/{folder2}/",
                f"https://media.forgecdn.net/files/{folder1}/{folder2}/",
            ]
            
            # You may need to scrape or use alternative method
            return None
            
        except Exception as e:
            self.log(f"Error getting file URL: {str(e)}")
            return None
    
    def create_modpack_info_from_manifest(self, manifest: Dict, modpack_name: str) -> bool:
        """Create modpack_info.json from manifest.json"""
        try:
            modpack_dir = os.path.join(self.launcher.MODPACKS_DIR, modpack_name)
            
            # Extract CurseForge info
            name = manifest.get('name', modpack_name)
            version = manifest.get('version', '1.0.0')
            author = manifest.get('author', 'Unknown')
            
            # Get Minecraft version
            minecraft_version = None
            for loader in manifest.get('minecraft', {}).get('version', []):
                if isinstance(loader, str):
                    minecraft_version = loader
                    break
            
            # Get modloader info
            modloader = 'Vanilla'
            modloader_version = ''
            
            loaders = manifest.get('minecraft', {}).get('modLoaders', [])
            for loader in loaders:
                loader_id = loader.get('id', '').lower()
                if 'forge' in loader_id:
                    modloader = 'Forge'
                    modloader_version = loader_id.replace('forge-', '')
                    break
                elif 'fabric' in loader_id:
                    modloader = 'Fabric'
                    modloader_version = loader_id.replace('fabric-', '')
                    break
                elif 'neoforge' in loader_id:
                    modloader = 'NeoForge'
                    modloader_version = loader_id.replace('neoforge-', '')
                    break
            
            # Count downloaded mods
            mods_dir = os.path.join(modpack_dir, 'mods')
            mod_count = 0
            if os.path.exists(mods_dir):
                mod_count = len([f for f in os.listdir(mods_dir) if f.endswith('.jar')])
            
            info = {
                'name': name,
                'description': manifest.get('description', f'CurseForge modpack: {name}'),
                'author': author,
                'version': version,
                'created': modpack_dir,
                'minecraft_version': minecraft_version or '1.20.4',
                'modloader': modloader,
                'modloader_version': modloader_version,
                'source': 'CurseForge',
                'total_mods': len(manifest.get('files', [])),
                'downloaded_mods': mod_count
            }
            
            info_path = os.path.join(modpack_dir, 'modpack_info.json')
            with open(info_path, 'w', encoding='utf-8') as f:
                json.dump(info, f, indent=2, ensure_ascii=False)
            
            self.log(f"✅ Modpack info created: {info_path}")
            return True
            
        except Exception as e:
            self.log(f"❌ Error creating modpack info: {str(e)}")
            return False
    
    def import_curseforge_zip(self, zip_path: str, modpack_name: str = None) -> bool:
        """Full process: import CurseForge modpack from zip file"""
        try:
            if not os.path.exists(zip_path):
                self.log(f"❌ File not found: {zip_path}")
                return False
            
            # Get modpack name from zip if not provided
            if not modpack_name:
                modpack_name = Path(zip_path).stem
            
            # Sanitize name
            modpack_name = "".join(c for c in modpack_name if c.isalnum() or c in (' ', '-', '_')).strip()
            if not modpack_name:
                modpack_name = "curseforge_modpack"
            
            self.log(f"📦 Importing CurseForge modpack: {modpack_name}")
            
            # Read manifest
            manifest = self.get_modpack_info_from_zip(zip_path)
            if not manifest:
                return False
            
            # Extract overrides (configs, resourcepacks, etc.)
            if not self.extract_modpack_files(zip_path, modpack_name):
                return False
            
            # Create initial modpack_info.json
            if not self.create_modpack_info_from_manifest(manifest, modpack_name):
                return False
            
            # Download mods in background thread
            threading.Thread(
                target=self._download_mods_thread,
                args=(manifest, modpack_name),
                daemon=True
            ).start()
            
            return True
            
        except Exception as e:
            self.log(f"❌ Error importing modpack: {str(e)}")
            return False
    
    def _download_mods_thread(self, manifest: Dict, modpack_name: str):
        """Background thread for downloading mods"""
        try:
            success = self.download_mods_from_manifest(manifest, modpack_name)
            
            # Update modpack_info.json with final status
            modpack_dir = os.path.join(self.launcher.MODPACKS_DIR, modpack_name)
            info_path = os.path.join(modpack_dir, 'modpack_info.json')
            
            if os.path.exists(info_path):
                with open(info_path, 'r', encoding='utf-8') as f:
                    info = json.load(f)
                
                mods_dir = os.path.join(modpack_dir, 'mods')
                mod_count = len([f for f in os.listdir(mods_dir) if f.endswith('.jar')]) if os.path.exists(mods_dir) else 0
                
                info['downloaded_mods'] = mod_count
                info['import_complete'] = success
                
                with open(info_path, 'w', encoding='utf-8') as f:
                    json.dump(info, f, indent=2, ensure_ascii=False)
            
            self.launcher.refresh_modpacks_list()
            
        except Exception as e:
            self.log(f"❌ Error in download thread: {str(e)}")