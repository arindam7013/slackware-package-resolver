import os
from resolver import Resolver, InstallationPlan
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

SBO_MIRROR = "https://slackonly.com/pub/packages/15.0-x86_64/"

def display_menu():
    print("\n--- Slackware Package Resolver ---")
    print("1. List all available packages")
    print("2. Show dependency tree for a package")
    print("3. Install a package")
    print("4. Exit")
    print("------------------------------------")

def display_installation_plan(plan: InstallationPlan):
    print("\n--- Installation Plan ---")
    if plan.to_install:
        print(f"  Packages to install: {', '.join(plan.to_install)}")
    if plan.to_upgrade:
        print(f"  Packages to upgrade: {', '.join(plan.to_upgrade)}")
    if plan.already_installed:
        print(f"  Already installed (latest version): {', '.join(plan.already_installed)}")
    print("-------------------------")

def handle_installation_session(resolver: Resolver):
    try:
        package_names_str = input("Enter package name(s) to install: ").strip()
        if not package_names_str:
            print("\nError: Package name cannot be empty.")
            return
        packages_to_install = package_names_str.split()

        print("\nChoose a solver:")
        print("1. Topological Sort (Fast, for simple cases)")
        print("2. SAT Solver (Powerful, for complex conflicts)")
        solver_choice = input("Enter solver choice (1-2): ").strip()
        solver_type = 'sat' if solver_choice == '2' else 'topsort'

        print("\nCreating installation plan...")
        plan = resolver.create_installation_plan(packages_to_install, solver_type=solver_type)
        display_installation_plan(plan)
        
        if not plan.to_install and not plan.to_upgrade:
            print("\nAll requested packages are already installed and up to date.")
            return

        confirm = input("\nDo you want to proceed with this plan? (yes/no): ").strip().lower()
        if confirm == 'yes':
            execute_plan(resolver, plan)
        else:
            print("Aborting.")

    except (ValueError, RuntimeError) as e:
        print(f"\nError: {e}")

def execute_plan(resolver: Resolver, plan: InstallationPlan):
    print("\nExecuting plan...")
    all_packages = plan.to_install + plan.to_upgrade
    
    download_successful = resolver.download_packages(all_packages, SBO_MIRROR, "packages")
    if not download_successful:
        print("\nError: Halting due to download failure.")
        return
    
    print("Downloads complete.")
    print("Attempting real installation...")

    for pkg in all_packages:
        files = resolver.slackware.find_package_files(pkg, "packages")
        if files:
            success, msg = resolver.slackware.install_package(files[0])
            if not success:
                print(f"  Failed to install {pkg}: {msg}")
        else:
            print(f"  Error: Could not find downloaded file for {pkg}")
    
    resolver.invalidate_cache()

def main():
    resolver = Resolver(sbo_path='../slackbuilds')
    while True:
        display_menu()
        choice = input("Enter your choice (1-4): ")
        if choice == '1':
            packages = resolver.list_packages()
            print("\nAvailable packages:")
            for i in range(0, len(packages), 4):
                print("    ".join(f"{p:<18}" for p in packages[i:i+4]))
        elif choice == '2':
            try:
                pkg = input("Enter package name to inspect: ").strip()
                print(resolver.explain(pkg))
            except (ValueError, RuntimeError) as e:
                print(f"\nError: {e}")
        elif choice == '3':
            handle_installation_session(resolver)
        elif choice == '4':
            print("\nExiting.")
            break
        else:
            print("\nInvalid choice.")

if __name__ == "__main__":
    main()