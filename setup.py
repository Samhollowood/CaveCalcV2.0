import os
import sys
import subprocess
import shutil
import re 
import platform

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

# Check system meets basic requirements
assert sys.platform in ('darwin', 'linux', 'win32'), \
    "Platform not supported: %s" % (sys.platform)
assert sys.version_info >= (3, 0), \
    "Python version not supported. Python 3.5+ is recommended."

# Define install_requires
install_requires = [
    'scipy', 'numpy', 'matplotlib', 'inflection', 'phreeqpy', 'seaborn', 'pandas'
]

# If running on Windows, add pywin32
if sys.platform.lower() == 'win32':
    install_requires.append('pywin32')


setup(
    name='cavecalc',
    description='Cave Geochemical Modelling',
    author='Samuel Hollowood',
    author_email='samuel.hollowood@bnc.ox.ac.uk',
    url='https://www.earth.ox.ac.uk/people/samuel-hollowood',
    version='2.0',
    packages=['cavecalc', 'cavecalc.data', 'cavecalc.gui'],
    package_data={'cavecalc.data': ['*.dat']},
    scripts=['scripts/cc_input_gui.py', 'scripts/cc_output_gui.py'],
    install_requires=install_requires
    entry_points={
        'console_scripts': [
            'cc-config-phreeqpy = cavecalc.configure_phreeqpy:main',
        ],
    },
)

# Additional setup for non-Windows platforms (if Binder is Linux or macOS)
if sys.argv[1] == 'install' and sys.platform.lower() not in ['win32']:
    try:
        import phreeqpy
        print("Done\nAttempting to patch phreeqpy using 2to3...")
        loc = os.path.dirname(os.path.abspath(phreeqpy.__file__))
        com_file = os.path.join(loc, 'iphreeqc', 'phreeqc_com.py')
        subprocess.check_call(["2to3", "-w", com_file])
    except ImportError as e:
        print(f"phreeqpy not found: {e}")

# Skip Windows-specific steps (phreeqpy configuration for Windows)
if sys.platform.lower() == 'win32':
    try:
        print("Configuring phreeqpy for Windows...")

        # Locate phreeqpy installation
        output = subprocess.check_output([sys.executable, '-m', 'pip', 'show', 'phreeqpy'], universal_newlines=True)
        phreeqpy_path = None
        for line in output.splitlines():
            if line.startswith('Location:'):
                phreeqpy_path = line.split('Location: ')[1]
                break
            
        if not phreeqpy_path:
            raise FileNotFoundError("phreeqpy installation path not found. Ensure it is installed.")

        # Paths to IPhreeqc files
        iphreeqc_path = os.path.join(phreeqpy_path, 'phreeqpy', 'iphreeqc')
        iphreeqc_dll_path = os.path.join(iphreeqc_path, 'IPhreeqc.dll')
        iphreeqc_backup_path = os.path.join(iphreeqc_path, 'IPhreeqc_backup.dll')
        iphreeqc_phreeqc3_path = os.path.join(iphreeqc_path, 'phreeqc3')

        # Check if the phreeqc3 directory exists
        if not os.path.exists(iphreeqc_phreeqc3_path):
            raise FileNotFoundError(f"phreeqc3 directory not found at {iphreeqc_phreeqc3_path}")

        # If the backup file already exists, delete it
        if os.path.exists(iphreeqc_backup_path):
            os.remove(iphreeqc_backup_path)
            print(f"Deleted existing {iphreeqc_backup_path}")

        # Rename the current IPhreeqc.dll to backup (if it exists)
        if os.path.exists(iphreeqc_dll_path):
            os.rename(iphreeqc_dll_path, iphreeqc_backup_path)
            print(f"Renamed {iphreeqc_dll_path} to {iphreeqc_backup_path}")

        # Find IPhreeqc-x.x.x.dll file in phreeqc3
        dll_files = [f for f in os.listdir(iphreeqc_phreeqc3_path) if f.startswith('IPhreeqc-') and f.endswith('.dll')]
        if not dll_files:
            raise FileNotFoundError("No IPhreeqc-x.x.x.dll file found in phreeqc3 directory.")

        iphreeqc_versioned_dll_path = os.path.join(iphreeqc_phreeqc3_path, dll_files[0])

        # Rename the current IPhreeqc.dll to backup
        if os.path.exists(iphreeqc_dll_path):
            os.rename(iphreeqc_dll_path, iphreeqc_backup_path)

        # Copy the versioned IPhreeqc-x.x.x.dll to IPhreeqc.dll
        shutil.copy(iphreeqc_versioned_dll_path, iphreeqc_dll_path)
        print(f"Copied {dll_files[0]} to {iphreeqc_dll_path}")

    except Exception as e:
        print(f"Error during phreeqpy configuration: {e}")

# For Linux
if sys.platform.lower() == 'linux':
    try:
        print("Configuring phreeqpy for Linux...")

        # Locate phreeqpy installation
        output = subprocess.check_output([sys.executable, '-m', 'pip', 'show', 'phreeqpy'], universal_newlines=True)
        phreeqpy_path = None
        for line in output.splitlines():
            if line.startswith('Location:'):
                phreeqpy_path = line.split('Location: ')[1]
                break

        if not phreeqpy_path:
            raise FileNotFoundError("phreeqpy installation path not found. Ensure it is installed.")

        # Paths to IPhreeqc files
        iphreeqc_path = os.path.join(phreeqpy_path, 'phreeqpy', 'iphreeqc')
        iphreeqc_so_path = os.path.join(iphreeqc_path, 'libiphreeqc.so.0.0.0')
        iphreeqc_backup_path = os.path.join(iphreeqc_path, 'libiphreeqc_backup.so')
        iphreeqc_phreeqc3_path = os.path.join(iphreeqc_path, 'phreeqc3')

        # Find all libiphreeqc-<version>.so files (with dynamic version)
        so_files = [f for f in os.listdir(iphreeqc_phreeqc3_path) if re.match(r'libiphreeqc-\d+\.\d+\.\d+\.so', f)]
        if not so_files:
            raise FileNotFoundError("No libiphreeqc-<version>.so file found in phreeqc3 directory.")

        # Assuming we want the first found file (or you can implement version sorting if needed)
        iphreeqc_versioned_so_path = os.path.join(iphreeqc_phreeqc3_path, so_files[0])

        # Check if the phreeqc3 directory exists
        if not os.path.exists(iphreeqc_phreeqc3_path):
            raise FileNotFoundError(f"phreeqc3 directory not found at {iphreeqc_phreeqc3_path}")

        # If the backup file already exists, delete it
        if os.path.exists(iphreeqc_backup_path):
            os.remove(iphreeqc_backup_path)
            print(f"Deleted existing {iphreeqc_backup_path}")

        # Rename the current libiphreeqc.so.0.0.0 to backup (if it exists)
        if os.path.exists(iphreeqc_so_path):
            os.rename(iphreeqc_so_path, iphreeqc_backup_path)
            print(f"Renamed {iphreeqc_so_path} to {iphreeqc_backup_path}")

        # Copy the versioned libiphreeqc.so to libiphreeqc.so
        shutil.copy(iphreeqc_versioned_so_path, iphreeqc_so_path)
        print(f"Copied {iphreeqc_versioned_so_path} to {iphreeqc_so_path}")

    except Exception as e:
        print(f"An error occurred while configuring phreeqpy for Linux: {e}")

print("Cavecalc installation complete. Run example1.py to test.")






