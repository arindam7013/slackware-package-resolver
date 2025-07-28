# slack_tools.py

import subprocess
import re
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import logging
import glob
import os

logger = logging.getLogger(__name__)

class SlackwareTools:
    """A class to interact with Slackware's native package tools."""
    
    def __init__(self):
        self.packages_dir = Path("/var/log/packages")

    def get_installed_packages(self) -> Dict[str, Dict]:
        """Gets a list of all installed packages with their details."""
        installed = {}
        if not self.packages_dir.exists():
            return installed
            
        for package_file in self.packages_dir.iterdir():
            if package_file.is_file():
                try:
                    package_info = self._parse_installed_package(package_file)
                    if package_info:
                        installed[package_info['name']] = package_info
                except Exception as e:
                    logger.warning(f"Could not parse package file {package_file}: {e}")
        return installed

    def _parse_installed_package(self, package_file: Path) -> Optional[Dict]:
        """Parses a package's name, version, arch, and build from its filename."""
        filename = package_file.name
        parts = filename.split('-')
        if len(parts) < 4:
            return None
        
        # This logic correctly handles names with hyphens (e.g., python-requests)
        build = parts[-1]
        arch = parts[-2]
        version = parts[-3]
        name = '-'.join(parts[:-3])
        
        return {'name': name, 'version': version, 'arch': arch, 'build': build}

    def install_package(self, package_path: str) -> Tuple[bool, str]:
        """Installs a package using the 'installpkg' command."""
        if not os.path.exists(package_path):
            return False, f"Package file not found: {package_path}"
        
        # Inside the container, we run as root, so no sudo is needed.
        cmd = ['installpkg', package_path]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            if result.returncode == 0:
                logger.info(f"Successfully installed: {os.path.basename(package_path)}")
                return True, result.stdout
            else:
                logger.error(f"Installation failed: {result.stderr}")
                return False, result.stderr
        except (subprocess.TimeoutExpired, subprocess.SubprocessError) as e:
            return False, f"Installation process error: {e}"

    def find_package_files(self, package_name: str, cache_dir: str) -> List[str]:
        """Finds downloaded package files that match a given package name."""
        # Use a more robust glob pattern to find the file
        pattern = f"{cache_dir}/*{package_name}-*.t?z"
        return glob.glob(pattern)