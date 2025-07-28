import os
from resolver import Resolver

# Define the mirror for SBo binary packages
SBO_MIRROR = "https://slackonly.com/pub/packages/15.0-x86_64/"

def display_menu():
    """Prints the main menu options to the console."""
    print("\n--- Slackware Package Resolver Menu ---")
    print("1. List all available packages")
    print("2. Show dependency tree for a package")
    print("3. Install a package")
    print("4. Exit")
    print("---------------------------------------")

def list_all_packages(resolver):
    """Prints a formatted list of all available packages."""
    print("\n📦 Available packages:")
    packages = resolver.list_packages()
    for i in range(0, len(packages), 4):
        print("    ".join(f"{p:<18}" for p in packages[i:i+4]))

def show_dependency_tree(resolver):
    """Asks for a package name and prints its dependency tree."""
    try:
        package_name = input("Enter the package name to inspect: ").strip()
        if not package_name:
            print("\n Error: Package name cannot be empty.")
            return
            
        print(f"\n Dependency tree for '{package_name}':")
        explanation = resolver.explain(package_name)
        print(explanation)
    except (ValueError, RuntimeError) as e:
        print(f"\n {e}")

def handle_installation_session(resolver):
    """Manages all user interaction for an installation task."""
    try:
        package_names_str = input("Enter package names to install (separated by spaces): ").strip()
        if not package_names_str:
            print("\n Error: Package name cannot be empty.")
            return
        packages_to_install = package_names_str.split()

        print("\nChoose a solver:")
        print("1. Topological Sort (Fast, for simple cases)")
        print("2. SAT Solver (Powerful, for complex conflicts)")
        solver_choice = input("Enter solver choice (1-2): ").strip()

        if solver_choice not in ['1', '2']:
            print("\n Invalid solver choice. Aborting.")
            return

        run_confirm = input("Perform real installation? (yes/no) [default: no]: ").strip().lower()
        run_mode = True if run_confirm == 'yes' else False

        run_resolver_and_install(resolver, packages_to_install, solver_choice, run_mode)

    except (ValueError, RuntimeError) as e:
        print(f"\n {e}")

def run_resolver_and_install(resolver, packages_to_install, solver_choice, run_mode):
    """Resolves, downloads, and installs packages."""
    print(f"\n  Resolving dependencies for: {', '.join(packages_to_install)}...")
    
    install_order = []
    if solver_choice == '1':
        install_order = resolver.resolve_with_topsort(packages_to_install)
    else: # solver_choice == '2'
        install_order = resolver.resolve_with_sat(packages_to_install)
    
    if not install_order:
         print("\n Nothing to install or resolve.")
         return

    print("\n Installation order determined:")
    print(" -> ".join(install_order))

    if run_mode:
        resolver.download_packages(install_order, SBO_MIRROR, "packages")
        print(" Downloads complete.")

        print("\n RUN MODE ACTIVATED. Attempting real installation... 🚨")
        for package in install_order:
            command = f"installpkg packages/{package}-*.t?z"
            print(f"Executing: {command}")
            os.system(command)
        print("\n Installation commands executed.")
    else:
        print("\n(This was a simulation. No packages will be downloaded or installed.)")

def main():
    """Runs the main menu loop for the application."""
    resolver = Resolver(sbo_path='../slackbuilds')
    
    while True:
        display_menu()
        choice = input("Enter your choice (1-4): ")

        if choice == '1':
            list_all_packages(resolver)
        elif choice == '2':
            show_dependency_tree(resolver)
        elif choice == '3':
            handle_installation_session(resolver)
        elif choice == '4':
            print("\n Exiting the program. Goodbye!")
            break
        else:
            print("\n Invalid choice. Please enter a number between 1 and 4.")

if __name__ == "__main__":
    main()