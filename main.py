import os
from resolver import Resolver, InstallationPlan
import logging
import requests

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

# Potential SlackOnly mirror URLs to try
POTENTIAL_MIRRORS = [
    "https://packages.slackonly.com/pub/packages/15.0-x86_64/",
    "https://slackonly.com/pub/packages/15.0-x86_64/",
    "https://bear.alienbase.nl/mirrors/slackonly/15.0-x86_64/",
    "https://mirror.slackonly.com/pub/packages/15.0-x86_64/",
    "https://slackonly.com/packages/15.0-x86_64/"
]

def test_mirror(mirror_url):
    """Test if a mirror URL is accessible by checking for CHECKSUMS.md5"""
    print(f"Testing mirror: {mirror_url}")
    try:
        response = requests.get(mirror_url + "CHECKSUMS.md5", timeout=15)
        if response.status_code == 200:
            # Also check if it has actual content
            if len(response.text) > 100:  # Basic sanity check
                print(f"   Mirror is working and has content")
                return True
            else:
                print(f"   Mirror accessible but no content")
                return False
        else:
            print(f"   HTTP {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"   Connection failed: {e}")
        return False

def find_working_mirror():
    """Find the first working mirror from the list"""
    print(" Searching for working SlackOnly mirror...")
    
    for mirror in POTENTIAL_MIRRORS:
        if test_mirror(mirror):
            print(f"✓ Using working mirror: {mirror}")
            return mirror
    
    # If no mirrors work, let user specify manually
    print("\n No working mirrors found automatically.")
    print("Please visit https://packages.slackonly.com/ to find the correct URL structure.")
    
    custom_url = input("Enter custom mirror URL (or press Enter to use default): ").strip()
    if custom_url:
        if not custom_url.endswith('/'):
            custom_url += '/'
        return custom_url
    else:
        print(f"Using default mirror (may not work): {POTENTIAL_MIRRORS[0]}")
        return POTENTIAL_MIRRORS[0]

# Find working mirror at startup
SBO_MIRROR = find_working_mirror()

def display_menu():
    print("\n--- Slackware Package Resolver ---")
    print("1. List all available packages")
    print("2. Show dependency tree for a package")
    print("3. Install a package")
    print("4. Test mirror connectivity")
    print("5. Exit")
    print("------------------------------------")

def display_installation_plan(plan: InstallationPlan):
    print("\n--- Installation Plan ---")
    if plan.to_install:
        print(f"   Packages to install: {', '.join(plan.to_install)}")
    if plan.to_upgrade:
        print(f"    Packages to upgrade: {', '.join(plan.to_upgrade)}")
    if plan.already_installed:
        print(f"   Already installed (latest version): {', '.join(plan.already_installed)}")
    print("-------------------------")

def handle_installation_session(resolver: Resolver):
    try:
        package_names_str = input("Enter package name(s) to install: ").strip()
        if not package_names_str:
            print("\n Error: Package name cannot be empty.")
            return
        packages_to_install = package_names_str.split()

        print("\nChoose a solver:")
        print("1. Topological Sort (Fast, for simple cases)")
        print("2. SAT Solver (Powerful, for complex conflicts)")
        solver_choice = input("Enter solver choice (1-2): ").strip()
        solver_type = 'sat' if solver_choice == '2' else 'topsort'

        print("\n Creating installation plan...")
        plan = resolver.create_installation_plan(packages_to_install, solver_type=solver_type)
        display_installation_plan(plan)
        
        if not plan.to_install and not plan.to_upgrade:
            print("\n All requested packages are already installed and up to date.")
            return

        confirm = input("\n Do you want to proceed with this plan? (yes/no): ").strip().lower()
        if confirm in ['yes', 'y']:
            execute_plan(resolver, plan)
        else:
            print(" Installation aborted.")

    except (ValueError, RuntimeError) as e:
        print(f"\n Error: {e}")

def execute_plan(resolver: Resolver, plan: InstallationPlan):
    print("\n Executing installation plan...")
    all_packages = plan.to_install + plan.to_upgrade
    
    try:
        download_successful = resolver.download_packages(all_packages, SBO_MIRROR, "packages")
        if not download_successful:
            print(f"\n Some downloads failed. Check if {SBO_MIRROR} is the correct mirror URL.")
            print("You can try option 4 to test mirror connectivity.")
            return
        
        print(" Downloads complete.")
        print(" Attempting package installation...")

        success_count = 0
        for pkg in all_packages:
            files = resolver.slackware.find_package_files(pkg, "packages")
            if files:
                success, msg = resolver.slackware.install_package(files[0])
                if success:
                    print(f"   Successfully installed {pkg}")
                    success_count += 1
                else:
                    print(f"   Failed to install {pkg}: {msg}")
            else:
                print(f"   Error: Could not find downloaded file for {pkg}")
        
        print(f"\n Installation Summary: {success_count}/{len(all_packages)} packages installed successfully")
        resolver.invalidate_cache()
        
    except Exception as e:
        print(f"\n Installation failed: {e}")

def test_mirror_connectivity():
    """Manual mirror testing function"""
    global SBO_MIRROR
    print(f"\n Current mirror: {SBO_MIRROR}")
    
    if test_mirror(SBO_MIRROR):
        print(" Current mirror is working!")
    else:
        print(" Current mirror is not working.")
        new_mirror = find_working_mirror()
        SBO_MIRROR = new_mirror
        print(f"Updated to: {SBO_MIRROR}")

def main():
    print(" Slackware Package Resolver")
    print("=" * 40)
    
    try:
        resolver = Resolver(sbo_path='../slackbuilds')
        print(" Resolver initialized successfully")
    except Exception as e:
        print(f" Failed to initialize resolver: {e}")
        return
    
    while True:
        display_menu()
        choice = input("Enter your choice (1-5): ").strip()
        
        if choice == '1':
            packages = resolver.list_packages()
            print(f"\n Available packages ({len(packages)} total):")
            for i in range(0, len(packages), 4):
                print("    ".join(f"{p:<18}" for p in packages[i:i+4]))
                
        elif choice == '2':
            try:
                pkg = input("Enter package name to inspect: ").strip()
                if pkg:
                    print(f"\n Dependency tree for '{pkg}':")
                    print(resolver.explain(pkg))
                else:
                    print(" Package name cannot be empty.")
            except (ValueError, RuntimeError) as e:
                print(f"\n Error: {e}")
                
        elif choice == '3':
            handle_installation_session(resolver)
            
        elif choice == '4':
            test_mirror_connectivity()
            
        elif choice == '5':
            print("\n Goodbye!")
            break
            
        else:
            print("\n Invalid choice. Please enter a number between 1-5.")

if __name__ == "__main__":
    main()