import os
import sys
import subprocess
import shutil
import re
from setuptools import setup, find_packages
from setuptools.command.install import install


class CustomInstallCommand(install):
    """Custom install command to configure phreeqpy after installation."""
    
    def run(self):
        # Run the standard install process
        install.run(self)
        
        # Post-install configuration
        try:
            output = subprocess.check_output([sys.executable, '-m', 'pip', 'show', 'phreeqpy'], universal_newlines=True)
            phreeqpy_path = next((line.split('Location: ')[1] for line in output.splitlines() if line.startswith('Location:')), None)
            if not phreeqpy_path:
                raise FileNotFoundError("phreeqpy installation path not found.")

            iphreeqc_path = os.path.join(phreeqpy_path, 'phreeqpy', 'iphreeqc')

            if sys.platform.lower() == 'win32':
                print("Configuring phreeqpy for Windows...")
                iphreeqc_dll_path = os.path.join(iphreeqc_path, 'IPhreeqc.dll')
                iphreeqc_phreeqc3_path = os.path.join(iphreeqc_path, 'phreeqc3')

                if not os.path.exists(iphreeqc_phreeqc3_path):
                    raise FileNotFoundError(f"phreeqc3 directory not found at {iphreeqc_phreeqc3_path}")

                dll_files = [f for f in os.listdir(iphreeqc_phreeqc3_path) if f.startswith('IPhreeqc-') and f.endswith('.dll')]
                if dll_files:
                    shutil.copy(os.path.join(iphreeqc_phreeqc3_path, dll_files[0]), iphreeqc_dll_path)
                    print(f"Copied {dll_files[0]} to {iphreeqc_dll_path}")

            elif sys.platform.lower() == 'linux':
                print("Configuring phreeqpy for Linux...")
                iphreeqc_so_path = os.path.join(iphreeqc_path, 'libiphreeqc.so.0.0.0')
                iphreeqc_phreeqc3_path = os.path.join(iphreeqc_path, 'phreeqc3')

                so_files = [f for f in os.listdir(iphreeqc_phreeqc3_path) if re.match(r'libiphreeqc-\d+\.\d+\.\d+\.so', f)]
                if so_files:
                    shutil.copy(os.path.join(iphreeqc_phreeqc3_path, so_files[0]), iphreeqc_so_path)
                    print(f"Copied {so_files[0]} to {iphreeqc_so_path}")

        except Exception as e:
            print(f"Error configuring phreeqpy: {e}")


# Ensure the platform and Python version are supported
assert sys.platform in ('darwin', 'linux', 'win32'), f"Platform not supported: {sys.platform}"
assert sys.version_info >= (3, 5), "Python version not supported. Python 3.5+ is recommended."

# Define install dependencies
install_requires = [
    'scipy', 'numpy', 'matplotlib', 'inflection', 'phreeqpy', 'seaborn', 'pandas'
]

# Windows-specific dependencies
if sys.platform.lower() == 'win32':
    install_requires.append('pywin32')

setup(
    name='cavecalc',
    version='2.0',
    description='Cave Geochemical Modelling',
    author='Samuel Hollowood',
    author_email='samuel.hollowood@bnc.ox.ac.uk',
    url='https://www.earth.ox.ac.uk/people/samuel-hollowood',
    packages=find_packages(),  # Automatically finds all packages
    package_data={'cavecalc.data': ['*.dat']},
    scripts=['scripts/cc_input_gui.py', 'scripts/cc_output_gui.py'],
    install_requires=install_requires,
    python_requires='>=3.5',
    cmdclass={'install': CustomInstallCommand},  # Ensures post-install script runs
)

print("Cavecalc installation complete. Run example1.py to test.")



