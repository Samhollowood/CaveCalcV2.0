import os
import sys
import subprocess
import shutil
import re
from setuptools import setup

# Check system meets basic requirements
assert sys.platform in ('darwin', 'linux', 'win32'), \
    f"Platform not supported: {sys.platform}"
assert sys.version_info >= (3, 5), \
    "Python version not supported. Python 3.5+ is recommended."

# Define install_requires
install_requires = [
    'scipy', 'numpy', 'matplotlib', 'inflection', 'phreeqpy', 'seaborn', 'pandas'
]

# If running on Windows, add pywin32
if sys.platform.lower() == 'win32':
    install_requires.append('pywin32')

# Remove any existing cavecalc package
try:
    print("Checking for existing cavecalc installations...")
    subprocess.check_call([sys.executable, '-m', 'pip', 'uninstall', '-y', 'cavecalc'])
    print("Old cavecalc version removed.")
except subprocess.CalledProcessError:
    print("No existing cavecalc installation found.")

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
    install_requires=install_requires,
    include_package_data=True
)

# Additional setup for non-Windows platforms
if 'install' in sys.argv and sys.platform.lower() not in ['win32']:
    try:
        import phreeqpy
        print("Attempting to patch phreeqpy using 2to3...")
        loc = os.path.dirname(os.path.abspath(phreeqpy.__file__))
        com_file = os.path.join(loc, 'iphreeqc', 'phreeqc_com.py')
        subprocess.check_call([sys.executable, '-m', 'lib2to3', '-w', com_file])
    except ImportError as e:
        print(f"phreeqpy not found: {e}")

# Platform-specific configuration
for platform in ['win32', 'linux']:
    if sys.platform.lower() == platform:
        try:
            print(f"Configuring phreeqpy for {platform}...")
            output = subprocess.check_output([sys.executable, '-m', 'pip', 'show', 'phreeqpy'], universal_newlines=True)
            phreeqpy_path = next((line.split('Location: ')[1] for line in output.splitlines() if line.startswith('Location:')), None)
            if not phreeqpy_path:
                raise FileNotFoundError("phreeqpy installation path not found. Ensure it is installed.")
            
            iphreeqc_path = os.path.join(phreeqpy_path, 'phreeqpy', 'iphreeqc')
            backup_path = os.path.join(iphreeqc_path, 'IPhreeqc_backup.dll' if platform == 'win32' else 'libiphreeqc_backup.so')
            phreeqc3_path = os.path.join(iphreeqc_path, 'phreeqc3')
            
            if not os.path.exists(phreeqc3_path):
                raise FileNotFoundError(f"phreeqc3 directory not found at {phreeqc3_path}")
            
            file_ext = '.dll' if platform == 'win32' else '.so'
            versioned_files = [f for f in os.listdir(phreeqc3_path) if re.match(fr'IPhreeqc-\d+\.\d+\.\d+{file_ext}', f)]
            if not versioned_files:
                raise FileNotFoundError(f"No IPhreeqc-<version>{file_ext} file found in phreeqc3 directory.")
            
            versioned_file_path = os.path.join(phreeqc3_path, versioned_files[0])
            target_path = os.path.join(iphreeqc_path, f'IPhreeqc{file_ext}')
            
            if os.path.exists(backup_path):
                os.remove(backup_path)
            if os.path.exists(target_path):
                os.rename(target_path, backup_path)
            shutil.copy(versioned_file_path, target_path)
            print(f"Copied {versioned_files[0]} to {target_path}")
        except Exception as e:
            print(f"Error configuring phreeqpy for {platform}: {e}")

print("Cavecalc installation complete. Run example1.py to test.")

