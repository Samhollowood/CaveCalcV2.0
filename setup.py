import os
import sys
import subprocess
import shutil
import re
from setuptools import setup, find_packages
from setuptools.command.install import install


class CustomInstallCommand(install):
    """Custom install command to rename and replace IPhreeqc.dll/libiphreeqc.so after installation."""

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
            iphreeqc_phreeqc3_path = os.path.join(iphreeqc_path, 'phreeqc3')

            if not os.path.exists(iphreeqc_phreeqc3_path):
                raise FileNotFoundError(f"phreeqc3 directory not found at {iphreeqc_phreeqc3_path}")

            if sys.platform.lower() == 'win32':
                print("Configuring phreeqpy for Windows...")

                iphreeqc_dll_path = os.path.join(iphreeqc_path, 'IPhreeqc.dll')
                iphreeqc_backup_path = os.path.join(iphreeqc_path, 'IPhreeqc_backup.dll')

                # Rename the existing IPhreeqc.dll to IPhreeqc_backup.dll
                if os.path.exists(iphreeqc_dll_path):
                    shutil.move(iphreeqc_dll_path, iphreeqc_backup_path)
                    print(f"Renamed existing DLL to {iphreeqc_backup_path}")

                # Find the latest versioned IPhreeqc-x.x.x.dll
                dll_files = [f for f in os.listdir(iphreeqc_phreeqc3_path) if re.match(r'IPhreeqc-\d+\.\d+\.\d+\.dll', f)]
                if dll_files:
                    latest_dll = sorted(dll_files, reverse=True)[0]  # Get latest version
                    shutil.copy(os.path.join(iphreeqc_phreeqc3_path, latest_dll), iphreeqc_dll_path)
                    print(f"Copied {latest_dll} to {iphreeqc_dll_path}")
                else:
                    print("No versioned IPhreeqc DLL found.")

            elif sys.platform.lower() == 'linux':
                print("Configuring phreeqpy for Linux...")

                iphreeqc_so_path = os.path.join(iphreeqc_path, 'libiphreeqc.so.0.0.0')
                iphreeqc_backup_path = os.path.join(iphreeqc_path, 'libiphreeqc_backup.so.0.0.0')

                # Rename the existing libiphreeqc.so.0.0.0 to libiphreeqc_backup.so.0.0.0
                if os.path.exists(iphreeqc_so_path):
                    shutil.move(iphreeqc_so_path, iphreeqc_backup_path)
                    print(f"Renamed existing shared object to {iphreeqc_backup_path}")

                # Find the latest versioned libiphreeqc-x.x.x.so
                so_files = [f for f in os.listdir(iphreeqc_phreeqc3_path) if re.match(r'libiphreeqc-\d+\.\d+\.\d+\.so', f)]
                if so_files:
                    latest_so = sorted(so_files, reverse=True)[0]  # Get latest version
                    shutil.copy(os.path.join(iphreeqc_phreeqc3_path, latest_so), iphreeqc_so_path)
                    print(f"Copied {latest_so} to {iphreeqc_so_path}")
                else:
                    print("No versioned libiphreeqc shared object found.")

        except Exception as e:
            print(f"Error configuring phreeqpy: {e}")


setup(
    name='cavecalc',
    version='2.0',
    description='Cave Geochemical Modelling',
    author='Samuel Hollowood',
    author_email='samuel.hollowood@bnc.ox.ac.uk',
    url='https://www.earth.ox.ac.uk/people/samuel-hollowood',
    packages=find_packages(),
    package_data={'cavecalc.data': ['*.dat']},
    scripts=['scripts/cc_input_gui.py', 'scripts/cc_output_gui.py'],
    install_requires=['scipy', 'numpy', 'matplotlib', 'inflection', 'phreeqpy', 'seaborn', 'pandas'],
    python_requires='>=3.5',
    cmdclass={'install': CustomInstallCommand},
)

print("Cavecalc installation complete. Run example1.py to test.")



