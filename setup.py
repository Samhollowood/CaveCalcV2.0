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
    f"Platform not supported: {sys.platform}"
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
)

# Utility function for phreeqpy configuration
def configure_phreeqpy_for_platform(iphreeqc_path, platform_type):
    try:
        # Locate phreeqpy installation
        output = subprocess.check_output([sys.executable, '-m', 'pip', 'show', 'phreeqpy'], universal_newlines=True)
        phreeqpy_path = None
        for line in output.splitlines():
            if line.startswith('Location:'):
                phreeqpy_path = line.split('Location: ')[1]
                break

        if not phreeqpy_path:
            raise FileNotFoundError("phreeqpy installation path not found. Ensure it is installed.")

        # Platform-specific file handling
        if platform_type == 'win32':
            iphreeqc_files = [f for f in os.listdir(iphreeqc_path) if f.startswith('IPhreeqc-') and f.endswith('.dll')]
            extension = '.dll'
            backup_extension = '_backup.dll'
        elif platform_type == 'linux':
            iphreeqc_files = [f for f in os.listdir(iphreeqc_path) if re.match(r'libiphreeqc-\d+\.\d+\.\d+\.so', f)]
            extension = '.so'
            backup_extension = '_backup.so'
        elif platform_type == 'darwin' and 'arm64' in platform.machine():
            iphreeqc_files = [f for f in os.listdir(iphreeqc_path) if f.startswith('libiphreeqc-') and f.endswith('-m1.dylib')]
            extension = '.dylib'
            backup_extension = '_backup.dylib'
        else:
            raise ValueError("Unsupported platform or architecture.")

        if not iphreeqc_files:
            raise FileNotFoundError(f"No appropriate {extension} file found in {iphreeqc_path}")

        # Handle backup and replacement
        for file in iphreeqc_files:
            source_path = os.path.join(iphreeqc_path, file)
            backup_path = os.path.join(iphreeqc_path, file.replace(extension, backup_extension))

            # Backup the existing file if it exists
            if os.path.exists(backup_path):
                os.remove(backup_path)

            # Rename existing file to backup if it exists
            if os.path.exists(source_path):
                os.rename(source_path, backup_path)

            # Copy the versioned file over to replace the old one
            shutil.copy(source_path, source_path.replace(extension, backup_extension))
            print(f"Copied {file} to {source_path.replace(extension, backup_extension)}")

    except Exception as e:
        print(f"Error during phreeqpy configuration for {platform_type}: {e}")

# For platform-specific handling
if sys.argv[1] == 'install':
    if sys.platform.lower() in ['win32', 'linux', 'darwin']:
        try:
            # Locate the phreeqpy installation folder
            output = subprocess.check_output([sys.executable, '-m', 'pip', 'show', 'phreeqpy'], universal_newlines=True)
            phreeqpy_path = None
            for line in output.splitlines():
                if line.startswith('Location:'):
                    phreeqpy_path = line.split('Location: ')[1]
                    break

            if not phreeqpy_path:
                raise FileNotFoundError("phreeqpy installation path not found. Ensure it is installed.")

            # Get path to iphreeqc folder
            iphreeqc_path = os.path.join(phreeqpy_path, 'phreeqpy', 'iphreeqc')

            # Call platform-specific configuration function
            configure_phreeqpy_for_platform(iphreeqc_path, sys.platform.lower())

        except Exception as e:
            print(f"An error occurred during phreeqpy configuration: {e}")

print("Cavecalc installation complete. Run example1.py to test.")



