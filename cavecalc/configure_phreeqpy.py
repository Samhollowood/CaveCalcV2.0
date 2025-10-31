# cavecalc/configure_phreeqpy.py
from __future__ import annotations
import sys, os, re, subprocess, shutil
from pathlib import Path

def find_phreeqpy_location():
    try:
        import phreeqpy
        return Path(phreeqpy.__file__).resolve().parents[0]  # <...>/phreeqpy
    except Exception:
        try:
            out = subprocess.check_output([sys.executable, '-m', 'pip', 'show', 'phreeqpy'],
                                          universal_newlines=True)
            for line in out.splitlines():
                if line.startswith('Location:'):
                    return Path(line.split('Location: ',1)[1]) / 'phreeqpy'
        except Exception:
            return None

def configure_windows(iphreeqc_path):
    phreeqc3 = iphreeqc_path / 'phreeqc3'
    if not phreeqc3.exists():
        raise FileNotFoundError(f"phreeqc3 directory not found at {phreeqc3}")
    dlls = [p for p in phreeqc3.iterdir() if p.name.startswith('IPhreeqc-') and p.suffix.lower()=='.dll']
    if not dlls:
        raise FileNotFoundError("No IPhreeqc-*.dll file found")
    target = iphreeqc_path / 'IPhreeqc.dll'
    backup = iphreeqc_path / 'IPhreeqc_backup.dll'
    if target.exists():
        target.rename(backup)
    shutil.copy2(dlls[0], target)
    print(f"Copied {dlls[0].name} -> {target}")

def configure_linux(iphreeqc_path):
    phreeqc3 = iphreeqc_path / 'phreeqc3'
    if not phreeqc3.exists():
        raise FileNotFoundError(f"phreeqc3 directory not found at {phreeqc3}")
    so_candidates = [p for p in phreeqc3.iterdir() if p.name.startswith('libiphreeqc')]
    if not so_candidates:
        raise FileNotFoundError("No libiphreeqc files found")
    chosen = so_candidates[0]
    target = iphreeqc_path / 'libiphreeqc.so.0.0.0'
    backup = iphreeqc_path / 'libiphreeqc_backup.so'
    if target.exists():
        target.rename(backup)
    shutil.copy2(chosen, target)
    print(f"Copied {chosen.name} -> {target}")

def main():
    loc = find_phreeqpy_location()
    if not loc:
        print("phreeqpy not found in the current environment. Install it and rerun this script.")
        return 2
    iphreeqc_path = loc / 'iphreeqc'
    if not iphreeqc_path.exists():
        raise FileNotFoundError(f"Expected iphreeqc path at {iphreeqc_path} not found")
    if sys.platform.startswith('win'):
        configure_windows(iphreeqc_path)
    elif sys.platform.startswith('linux'):
        configure_linux(iphreeqc_path)
    else:
        print(f"No automatic steps for platform {sys.platform}")
    print("phreeqpy configuration complete.")
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
