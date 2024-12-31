#!/usr/bin/env python3

import json
import os
import platform
import subprocess
import sys
from pathlib import Path

def read_config():
    config_path = Path("scripts/build_config.json")
    if not config_path.exists():
        print("Error: build_config.json not found")
        sys.exit(1)
    
    with open(config_path) as f:
        config = json.load(f)
    
    # Add repo_path to config
    config['repo_path'] = Path("external/aider")
    return config

def analyze_imports(config):
    from importlib.metadata import distributions
    import importlib

    # Read requirements.txt and clean up entries
    requirements = set()
    with open('requirements.txt', 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                # Split on any whitespace and take first part
                pkg = line.split()[0]
                # Remove version specifiers
                pkg = pkg.split('==')[0].split('>=')[0].split('<=')[0]
                requirements.add(pkg)

    # Build package to module mapping
    pkg_to_module = {}
    for dist in distributions():
        print(f"Checking package {dist.name}...")
        if dist.name in requirements:
            try:
                # Try to import the module with the same name as the package
                module_name = dist.name.replace('-', '_')  # Common replacement
                importlib.import_module(module_name)
                if module_name != dist.name:
                    print(f"Package {dist.name} has different module name: {module_name}")
                    pkg_to_module[dist.name] = module_name
            except ImportError as e:
                # If import fails, try to parse the actual module name from the error
                error_msg = str(e)
                if "No module named" in error_msg:
                    print(f"Package {dist.name} has no module name: {error_msg}")
    
    # Run PyInstaller with debug imports
    debug_output = subprocess.run(
        f"pyinstaller --debug=imports aider/main.py",
        shell=True,
        capture_output=True,
        text=True
    ).stdout
    
    # Parse debug output to find missing imports
    imported_modules = set()
    for line in debug_output.split('\n'):
        if 'LOADER: Import' in line:
            module = line.split()[2].split('.')[0]
            if module:  # Ensure we have a valid module name
                imported_modules.add(module)
    
    # Compare with requirements, using module names for PyInstaller
    missing_imports = set()
    for pkg in requirements:
        if pkg in pkg_to_module:
            # Use the mapped module name if we found one
            module_name = pkg_to_module[pkg]
            if module_name not in imported_modules:
                missing_imports.add(module_name)
        elif pkg not in imported_modules and not pkg.startswith('#'):
            # Default to package name with hyphens replaced by underscores
            module_name = pkg.replace('-', '_')
            missing_imports.add(module_name)
    
    return missing_imports
 
def build_project(config):
    # Create output directory
    output_dir = Path("dist")
    os.makedirs(output_dir, exist_ok=True)

    default_imports = [
        'aider',
        'aider.resources',
        'importlib_resources'
    ]
    
    # Analyze imports after dependencies are installed
    missing_imports = analyze_imports(config)
    
    # Combine default and analyzed imports
    all_imports = default_imports + list(missing_imports)
    hidden_imports = ' '.join(f'--hidden-import={imp}' for imp in all_imports)

    # Determine executable name based on OS
    if sys.platform.startswith('win'):
        exe_name = "aider.exe"
    else:
        exe_name = "aider"

    # Run build command
    print(f"Building executable for {sys.platform}...")
    arch = os.uname().machine if hasattr(os, 'uname') else platform.machine()
    
    build_command = (
        f"pyinstaller --onefile --hidden-import=aider {hidden_imports} "
        f"--collect-all aider aider/main.py "
        f"--name {exe_name}"
    )
    
    print(f"Build command: {build_command}")
    subprocess.run(build_command, shell=True, check=True)

def main():
    config = read_config()
    build_project(config)

if __name__ == "__main__":
    main()
