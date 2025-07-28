import json
import networkx as nx
from pysat.solvers import Glucose3
from itertools import combinations
from pathlib import Path
import re
import os
import requests
import logging
from dataclasses import dataclass
from typing import List, Dict, Optional

from slack_tools import SlackwareTools

logger = logging.getLogger(__name__)

@dataclass
class InstallationPlan:
    to_install: List[str]
    to_upgrade: List[str]
    already_installed: List[str]

class Resolver:
    def __init__(self, db_path='database.json', sbo_path='../slackbuilds'):
        with open(db_path, 'r', encoding='utf-8') as f:
            self.db = json.load(f)
        self.graph = self._build_dependency_graph()
        self.sbo_path = Path(sbo_path)
        self.slackware = SlackwareTools()
        self._installed_cache = None
        self._cache_valid = True

    def get_installed_packages(self) -> Dict[str, Dict]:
        if self._installed_cache is None or not self._cache_valid:
            self._installed_cache = self.slackware.get_installed_packages()
            self._cache_valid = True
        return self._installed_cache

    def invalidate_cache(self):
        self._cache_valid = False

    def create_installation_plan(self, packages_to_install: List[str], solver_type: str = 'topsort') -> InstallationPlan:
        if solver_type == 'sat':
            resolved_packages = self.resolve_with_sat(packages_to_install)
        else:
            resolved_packages = self.resolve_with_topsort(packages_to_install)
        
        installed = self.get_installed_packages()
        to_install = []
        to_upgrade = []
        already_installed = []

        for pkg in resolved_packages:
            if pkg in installed:
                db_version = self.db.get(pkg, {}).get('version', '0')
                installed_version = installed[pkg].get('version', '0')
                if db_version > installed_version:
                    to_upgrade.append(pkg)
                else:
                    already_installed.append(pkg)
            else:
                to_install.append(pkg)
        
        return InstallationPlan(
            to_install=to_install,
            to_upgrade=to_upgrade,
            already_installed=already_installed
        )

    def download_packages(self, packages_to_download, mirror_url, download_dir="packages"):
        os.makedirs(download_dir, exist_ok=True)
        manifest_url = mirror_url + "CHECKSUMS.md5"
        print(f"Downloading manifest from {manifest_url}...")
        try:
            response = requests.get(manifest_url, timeout=30)
            response.raise_for_status()
            manifest_data = response.text
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"Failed to download package manifest: {e}")

        # Enhanced package file parsing
        package_files = {}
        for line in manifest_data.splitlines():
            line = line.strip()
            if not line:
                continue
            
            parts = line.split()
            if len(parts) >= 2:
                filename = parts[-1]  # Last part is usually the filename
                if filename.endswith(('.txz', '.tgz', '.tbz', '.tlz')):
                    # Extract package name from filename
                    # Handle various naming patterns
                    basename = Path(filename).name
                    
                    # Try different extraction methods
                    pkg_names = self._extract_package_names(basename)
                    for pkg_name in pkg_names:
                        if pkg_name not in package_files:  # Don't overwrite existing entries
                            package_files[pkg_name] = filename

        def find_package_path(pkg_name):
            print(f"Searching for package: {pkg_name}")
            
            # Strategy 1: Exact match
            if pkg_name in package_files:
                print(f"  Found exact match: {package_files[pkg_name]}")
                return package_files[pkg_name]
            
            # Strategy 2: Case-insensitive match
            for key, value in package_files.items():
                if key.lower() == pkg_name.lower():
                    print(f"  Found case-insensitive match: {value}")
                    return value
            
            # Strategy 3: Partial match (contains)
            matches = []
            for key, value in package_files.items():
                if pkg_name.lower() in key.lower() or key.lower() in pkg_name.lower():
                    matches.append((key, value))
            
            if matches:
                # Prefer exact substring matches
                for key, value in matches:
                    if pkg_name.lower() == key.lower():
                        print(f"  Found partial exact match: {value}")
                        return value
                # Use first match if no exact match
                print(f"  Found partial match: {matches[0][1]} (for {matches[0][0]})")
                return matches[0][1]
            
            # Strategy 4: Common name variations
            name_variations = {
                "gtest": ["googletest", "gtest"],
                "lua": ["lua", "lua5.1", "lua53", "lua54"],
                "lua-lpeg": ["lpeg", "lua-lpeg", "lualpeg"],
                "lua-filesystem": ["luafilesystem", "lua-filesystem", "lfs"],
                "CorsixTH": ["corsixth", "CorsixTH", "corsix-th"]
            }
            
            variations = name_variations.get(pkg_name, [pkg_name])
            for variation in variations:
                if variation in package_files:
                    print(f"  Found variation match: {package_files[variation]}")
                    return package_files[variation]
            
            # Strategy 5: Directory-based search
            search_patterns = [
                f"/{re.escape(pkg_name)}/",
                f"/{re.escape(pkg_name.lower())}/",
                f"/{re.escape(pkg_name.upper())}/"
            ]
            
            for pattern in search_patterns:
                for line in manifest_data.splitlines():
                    if pattern in line:
                        parts = line.split()
                        if len(parts) >= 2 and parts[-1].endswith(('.txz', '.tgz', '.tbz', '.tlz')):
                            print(f"  Found directory-based match: {parts[-1]}")
                            return parts[-1]
            
            print(f"  No match found for: {pkg_name}")
            return None

        all_found = True
        for package in packages_to_download:
            file_path = find_package_path(package)
            if file_path:
                download_url = mirror_url + file_path.lstrip('./')
                local_filename = Path(download_dir) / Path(file_path).name
                print(f"Downloading {package} ({Path(file_path).name})...")
                try:
                    with requests.get(download_url, stream=True, timeout=60) as r:
                        r.raise_for_status()
                        with open(local_filename, 'wb') as f:
                            for chunk in r.iter_content(chunk_size=8192):
                                f.write(chunk)
                    print(f"  ✓ Downloaded {local_filename}")
                except requests.exceptions.RequestException as e:
                    print(f"  ✗ Failed to download {package}: {e}")
                    all_found = False
            else:
                print(f"  ✗ Could not find package '{package}' in the mirror manifest.")
                all_found = False
        return all_found

    def _extract_package_names(self, filename):
        """Extract possible package names from a filename"""
        names = []
        
        # Remove file extensions
        base = filename
        for ext in ['.txz', '.tgz', '.tbz', '.tlz']:
            if base.endswith(ext):
                base = base[:-len(ext)]
                break
        
        # Split by common separators and try different combinations
        parts = re.split(r'[-_]', base)
        
        if len(parts) >= 1:
            # First part is usually the package name
            names.append(parts[0])
            
            # Sometimes package name includes second part
            if len(parts) >= 2 and not re.match(r'^\d', parts[1]):  # Not a version
                names.append(f"{parts[0]}-{parts[1]}")
        
        # Add the full base name without version/arch/build
        # Try to identify version patterns
        version_match = re.search(r'-(\d+\.[\d\w\.\-]+)-[\w\d]+-\d+$', base)
        if version_match:
            pkg_name = base[:version_match.start()]
            names.append(pkg_name)
        
        return list(set(names))  # Remove duplicates

    def _build_dependency_graph(self):
        G = nx.DiGraph()
        for package, details in self.db.items():
            G.add_node(package)
            for dependency in details.get('requires', []):
                G.add_edge(package, dependency)
        return G
    
    def find_package_dynamically(self, package_name):
        if not self.sbo_path.is_dir():
            return []
        for category in self.sbo_path.iterdir():
            if category.is_dir():
                package_dir = category / package_name
                info_file = package_dir / f"{package_name}.info"
                if info_file.is_file():
                    parsed_info = self._parse_info_file(info_file)
                    if "PRGNAM" in parsed_info:
                        pkg_name = parsed_info["PRGNAM"]
                        requires_str = parsed_info.get("REQUIRES", "") or parsed_info.get("SLACKBOLT_REQUIRES", "")
                        deps = [dep for dep in requires_str.split() if not dep.startswith('%')]
                        self.db[pkg_name] = {"version": parsed_info.get("VERSION", "N/A"), "requires": deps}
                        self.graph.add_node(pkg_name)
                        for dep in deps:
                            self.graph.add_edge(pkg_name, dep)
                        return deps
        return []

    def _parse_info_file(self, file_path):
        info = {}
        keys_to_find = ["PRGNAM", "VERSION", "REQUIRES", "SLACKBOLT_REQUIRES"]
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                match = re.match(r'^\s*([A-Z_]+)\s*=\s*"(.*)"\s*$', line.strip())
                if match:
                    key, value = match.groups()
                    if key in keys_to_find:
                        info[key] = value
        return info

    def _ensure_packages_exist(self, packages):
        packages_to_check = list(packages)
        checked_packages = set()
        while packages_to_check:
            pkg = packages_to_check.pop(0)
            if pkg in checked_packages:
                continue
            checked_packages.add(pkg)
            if pkg not in self.db:
                print(f"'{pkg}' not in database, searching SBo repository...")
                new_deps = self.find_package_dynamically(pkg)
                if pkg not in self.db:
                     raise ValueError(f"Package '{pkg}' not found in database or SBo repository.")
                packages_to_check.extend(new_deps)

    def resolve_with_topsort(self, packages_to_install):
        self._ensure_packages_exist(packages_to_install)
        nodes_to_include = set()
        for pkg in packages_to_install:
            nodes_to_include.add(pkg)
            nodes_to_include.update(nx.descendants(self.graph, pkg))
        subgraph = self.graph.subgraph(nodes_to_include)
        try:
            install_order = list(nx.topological_sort(subgraph))
            install_order.reverse()
            return install_order
        except nx.NetworkXUnfeasible:
            raise RuntimeError("Topological sort failed. The request contains a circular dependency.")

    def resolve_with_sat(self, packages_to_install):
        self._ensure_packages_exist(packages_to_install)
        pkg_to_int = {pkg: i + 1 for i, pkg in enumerate(self.db.keys())}
        int_to_pkg = {i + 1: pkg for i, pkg in enumerate(self.db.keys())}
        clauses = []
        for pkg in packages_to_install:
            if pkg not in pkg_to_int:
                 raise ValueError(f"Package '{pkg}' not found for SAT solver.")
            clauses.append([pkg_to_int[pkg]])
        for pkg, details in self.db.items():
            for dep in details.get('requires', []):
                if dep in pkg_to_int:
                    clauses.append([-pkg_to_int[pkg], pkg_to_int[dep]])
        base_packages = {}
        for pkg, details in self.db.items():
            base = details.get("base_package")
            if base:
                base_packages.setdefault(base, []).append(pkg)
        for base, versions in base_packages.items():
            for v1, v2 in combinations(versions, 2):
                clauses.append([-pkg_to_int[v1], -pkg_to_int[v2]])
        with Glucose3(bootstrap_with=clauses) as solver:
            if solver.solve():
                model = solver.get_model()
                solution_packages = [int_to_pkg[i] for i in model if i > 0]
                subgraph = self.graph.subgraph(solution_packages)
                install_order = list(nx.topological_sort(subgraph))
                install_order.reverse()
                return install_order
            else:
                conflict_report = "SAT solver found a conflict!\n"
                from collections import defaultdict
                deps_of_requests = {}
                for pkg in packages_to_install:
                    deps = nx.descendants(self.graph, pkg)
                    deps.add(pkg)
                    deps_of_requests[pkg] = deps
                base_conflicts = defaultdict(list)
                for pkg, deps in deps_of_requests.items():
                    for dep in deps:
                        base = self.db.get(dep, {}).get("base_package")
                        if base:
                            base_conflicts[base].append(f"'{dep}' (required by '{pkg}')")
                for base, sources in base_conflicts.items():
                    if len(set(sources)) > 1:
                        conflict_report += f"  - Reason: Multiple versions of '{base}' are required.\n"
                        for source in sorted(list(set(sources))):
                            conflict_report += f"    - {source}\n"
                raise RuntimeError(conflict_report)

    def list_packages(self):
        return sorted(self.db.keys())

    def explain(self, package_name):
        self._ensure_packages_exist([package_name])
        nodes_to_include = nx.descendants(self.graph, package_name)
        nodes_to_include.add(package_name)
        subgraph = self.graph.subgraph(nodes_to_include)
        lines = []
        self._print_tree(subgraph, package_name, lines)
        return "\n".join(lines)

    def _print_tree(self, tree, node, lines, prefix="", is_last=True):
        lines.append(f"{prefix}{'└── ' if is_last else '├── '}{node}")
        children = list(tree.successors(node))
        for i, child in enumerate(children):
            new_prefix = prefix + ("    " if is_last else "│   ")
            self._print_tree(tree, child, lines, prefix=new_prefix, is_last=(i == len(children) - 1))