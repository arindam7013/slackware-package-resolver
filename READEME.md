# Slackware Package Resolver

A user-friendly, command-line package manager for Slackware Linux that provides automated dependency resolution using a powerful hybrid solver.

## The Problem

Slackware Linux is renowned for its simplicity and stability, but its traditional package management system (`pkgtool`) does not handle dependency resolution. This leaves the user with the manual, error-prone task of finding and installing all required dependencies, a process often referred to as "dependency hell." This can be a significant barrier for new users and a tedious task for experienced ones.

## The Solution

This project provides a complete, automated solution to this challenge. It is a smart package manager that enhances the Slackware experience without compromising its core philosophy of user control. The tool can analyze a package's requirements, download all necessary dependencies, and install them in the correct order, all while keeping the user informed and in command.

## Key Features

  * **Hybrid Dependency Resolver**: Utilizes a fast **Topological Sort** for simple, non-conflicting installations and automatically switches to a powerful **SAT Solver** to handle complex version conflicts and circular dependencies.
  * **Automated Database Creation**: Includes a script to build a comprehensive dependency database by parsing a local clone of the official **SlackBuilds.org (SBo)** repository.
  * **Dynamic Package Discovery**: Can find and resolve dependencies for packages on-the-fly, even if they are not in the pre-built database.
  * **"Plan and Execute" Workflow**: A core safety feature that first presents a clear, reviewable installation plan to the user. No changes are made to the system without explicit user confirmation.
  * **Fully Automated**: Handles the entire workflow: resolving dependencies, downloading packages from a binary repository, and installing them.
  * **System Compatibility**: Integrates cleanly with Slackware's native `installpkg` command, ensuring that all installations are fully compatible with the underlying system.
  * **User-Friendly Interface**: A simple, interactive menu-driven interface that guides the user through every step.

## Installation

1.  **Clone the Repository**:
    ```bash
    git clone https://github.com/arindam7013/slackware-package-resolver.git
    cd slackware-package-resolver
    ```
2.  **Create a Virtual Environment**:
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```
3.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

## Usage

### 1\. Build the Dependency Database

Before you can run the main application, you must first build the dependency database. This requires a local copy of the SlackBuilds.org repository.

  * **Clone the SBo Repository** (do this in the parent directory, alongside your project folder):
    ```bash
    # From the parent directory of your project
    git clone https://git.slackbuilds.org/slackbuilds/
    ```
  * **Run the Build Script** (from inside your project folder):
    ```bash
    python build_database.py ../slackbuilds
    ```

### 2\. Run the Application

Start the interactive menu with this command:

```bash
python main.py
```

From the menu, you can:

  * **List all available packages**: See all packages in the database.
  * **Show dependency tree**: Get a visual tree of a package's requirements.
  * **Install a package**: Start the automated installation workflow.

## Running Tests

To ensure the core resolver logic is working correctly, you can run the built-in test suite:

```bash
python -m unittest discover
```

## License

This project is licensed under the **MIT License**. See the `LICENSE` file for details.