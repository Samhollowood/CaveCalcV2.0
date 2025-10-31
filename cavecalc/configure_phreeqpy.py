# cavecalc/configure_phreeqpy.py
from __future__ import annotations
import sys
import os
import shutil
import subprocess
from pathlib import Path
import time

def find_phreeqpy_package_dir():
    try:
        import phreeqpy
        return Path(phreeqpy.__file__).resolve().parents[0]  # .../phreeqpy
    except Exception:
        # fallback to pip show
        try:
            out = subprocess.check_output([sys.executable, '-m', 'pip', 'show', 'phreeqpy'],
                                          universal_newlines=True)
            for line in out.splitlines():
                if line.startswith('Location:'):
                    loc = Path(line.split('Location: ', 1)[1]) / 'phreeqpy'
                    return loc
        except Exception:
            return None

def safe_replace(src: Path, dst: Path, make_backup: bool = True):
    """
    Replace dst with src safely.
    - If dst exists and make_backup True, move dst -> dst.backup.timestamp
    - Use os.replace to atomically overwrite when possible.
    """
    try:
        if dst.exists():
            if make_backup:
                ts = time.strftime("%Y%m%d%H%M%S")
                backup = dst.with_name(dst.name + f'.backup.{ts}')
                print(f"Creating backup: {backup}")
                # Use replace to move/overwrite backup if it somehow exists
                os.replace(str(dst), str(backup))
            else:
                # overwrite in-place
                os.replace(str(src), str(dst))
                return
        # copy src -> dst (preserve metadata)
        shutil.copy2(str(src), str(dst))
        print(f"Copied {src} -> {dst}")
    except PermissionError as e:
        raise PermissionError(f"Permission error while replacing {dst}: {e}")
    except OSError as e:
        # often happens on Windows if file is in use
        raise OSError(f"OS error while replacing {dst}: {e}")

def configure_windows(iphreeqc_path: Path):
    phreeqc3 = iphreeqc_path / 'phreeqc3'
    if not phreeqc3.exists():
        raise FileNotFoundError(f"phreeqc3 directory missing at {phreeqc3}")
    dlls = [p for p in phreeqc3.iterdir() if p.name.startswith('IPhreeqc-') and p.suffix.lower() == '.dll']
    if not dlls:
        raise FileNotFoundError(f"No IPhreeqc-*.dll found in {phreeqc3}; found: {[p.name for p in phreeqc3.iterdir()]}")
    versioned = dlls[0]
    target = iphreeqc_path / 'IPhreeqc.dll'
    try:
        # copy to a temp file then replace to avoid partial writes
        tmp = target.with_suffix('.tmp')
        shutil.copy2(versioned, tmp)
        safe_replace(tmp, target, make_backup=True)
    except Exception as e:
        raise RuntimeError(f"Windows configuration failed: {e}")

def configure_linux(iphreeqc_path: Path):
    phreeqc3 = iphreeqc_path / 'phreeqc3'
    if not phreeqc3.exists():
        raise FileNotFoundError(f"phreeqc3 directory missing at {phreeqc3}")
    # more flexible pattern than strict regex
    so_candidates = [p for p in phreeqc3.iterdir() if p.name.startswith('libiphreeqc')]
    if not so_candidates:
        raise FileNotFoundError(f"No libiphreeqc-* files found in {phreeqc3}; found: {[p.name for p in phreeqc3.iterdir()]}")
    chosen = so_candidates[0]
    # target name you expect; adjust if your phreeqpy version uses a different soname
    target = iphreeqc_path / 'libiphreeqc.so.0.0.0'
    try:
        tmp = target.with_suffix('.tmp')
        shutil.copy2(chosen, tmp)
        safe_replace(tmp, target, make_backup=True)
    except Exception as e:
        raise RuntimeError(f"Linux configuration failed: {e}")

def main():
    loc = find_phreeqpy_package_dir()
    if not loc:
        print("phreeqpy not found in this Python environment. Install it first and then run this script.")
        return 2
    iphreeqc_path = loc / 'iphreeqc'
    if not iphreeqc_path.exists():
        print(f"Expected iphreeqc at {iphreeqc_path} not found; contents of package dir: {list(loc.iterdir())}")
        return 3

    try:
        if sys.platform.startswith('win'):
            configure_windows(iphreeqc_path)
        elif sys.platform.startswith('linux'):
            configure_linux(iphreeqc_path)
        else:
            print(f"No automatic configuration implemented for platform {sys.platform}")
            return 4
    except Exception as e:
        print("Configuration failed:", e)
        print("Common causes: file is in use by another process, or you lack write permission.")
        print("On Windows, close any running Python interpreters (or services) that might be using phreeqpy and re-run the script as Administrator.")
        return 5

    print("phreeqpy configuration complete.")
    return 0

if __name__ == '__main__':
    raise SystemExit(main())

