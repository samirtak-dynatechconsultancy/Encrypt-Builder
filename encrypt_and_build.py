from pathlib import Path
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
import os
import subprocess
from collections import namedtuple

# --- Configuration ---

project_root = Path(os.getcwd()) / "validation_execution_project"
requirements_file = project_root / "requirements.txt"
requirements = requirements_file.read_text().splitlines()

package_name = "ge_validation_execution"
key = os.environ.get("TABLE_CLASSIFIER_KEY")
iv = os.environ.get("TABLE_CLASSIFIER_IV")

if key is None or iv is None:
    raise ValueError("❌ Missing TABLE_CLASSIFIER_KEY or TABLE_CLASSIFIER_IV in environment variables")

key = key.encode("utf-8")
iv = iv.encode("utf-8")
print("KEY", key)
print("IV", iv)

pkg_dir = project_root / package_name
loader_file = pkg_dir / "custom_loader.py"
init_file = pkg_dir / "__init__.py"

EncryptedModule = namedtuple("EncryptedModule", ["name", "plain_path", "enc_path", "rel_enc_path"])

# --- 1. Encrypt all .py files except __init__.py and setup.py ---
print("🔍 Finding .py files to encrypt...")
py_files = [f for f in pkg_dir.rglob("*.py")
            if f.name not in {"__init__.py", "setup.py"} and f.is_file()]

if not py_files:
    raise FileNotFoundError("❌ No .py files found to encrypt.")

encrypted_modules = []

for file in py_files:
    rel_path = file.relative_to(pkg_dir)
    enc_name = file.stem + "_encrypted"
    enc_filename = enc_name + ".enc"
    enc_path = file.with_name(enc_filename)
    rel_enc_path = rel_path.with_name(enc_filename)

    print(f"🔐 Encrypting {file} ➜ {enc_path}")
    plain_bytes = file.read_bytes()
    cipher = AES.new(key, AES.MODE_CBC, iv)
    encrypted = cipher.encrypt(pad(plain_bytes, AES.block_size))
    enc_path.write_bytes(encrypted)

    # Delete the original .py
    file.unlink()

    encrypted_modules.append(EncryptedModule(enc_name, file, enc_path, rel_enc_path))

# --- 2. Generate custom_loader.py ---
print("🧠 Writing custom_loader.py...")
loader_code = '''import importlib.abc
import importlib.util
import os
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad

class EncryptedModuleLoader(importlib.abc.Loader):
    def __init__(self, path, key, iv):
        self.path = path
        self.key = key
        self.iv = iv

    def create_module(self, spec):
        return None  # Default

    def exec_module(self, module):
        with open(self.path, "rb") as f:
            ciphertext = f.read()
        cipher = AES.new(self.key, AES.MODE_CBC, self.iv)
        decrypted = unpad(cipher.decrypt(ciphertext), AES.block_size)
        exec(decrypted, module.__dict__)

class EncryptedModuleFinder(importlib.abc.MetaPathFinder):
    def __init__(self, key, iv):
        self.key = key
        self.iv = iv
        self.module_map = {
'''
for mod in encrypted_modules:
    loader_code += f'            "{package_name}.{mod.name}": os.path.join(os.path.dirname(__file__), "{mod.rel_enc_path.as_posix()}"),\n'

loader_code += '''        }

    def find_spec(self, fullname, path, target=None):
        if fullname in self.module_map:
            enc_path = self.module_map[fullname]
            loader = EncryptedModuleLoader(enc_path, self.key, self.iv)
            return importlib.util.spec_from_loader(fullname, loader)
        return None
'''

loader_file.write_text(loader_code)

# --- 3. Overwrite __init__.py to install finder ---
print("📦 Updating __init__.py...")
init_code = f'''import sys
from .custom_loader import EncryptedModuleFinder
import os

key = os.environ.get("TABLE_CLASSIFIER_KEY")
iv = os.environ.get("TABLE_CLASSIFIER_IV")

if key is None or iv is None:
    raise ImportError("Encryption key/IV must be set in environment variables")

key = key.encode("utf-8")
iv = iv.encode("utf-8")

sys.meta_path.insert(0, EncryptedModuleFinder(key, iv))
'''
init_file.write_text(init_code)
import datetime
version = datetime.datetime.now().strftime("%Y.%m.%d.%H%M")

# --- 4. Write setup.py if not exists ---
import datetime
print("⚙️ Writing setup.py...")
enc_files_list = [f'"{mod.rel_enc_path.as_posix()}"' for mod in encrypted_modules]
version = datetime.datetime.now().strftime("%Y.%m.%d.%H%M")
requirements_file = project_root / "requirements.txt"
requirements = requirements_file.read_text().splitlines()

setup_code = f'''from setuptools import setup, find_packages

setup(
    name="{package_name}",
    version="{version}",
    packages=find_packages(),
    package_data={{
        "{package_name}": [{", ".join(enc_files_list)}]
    }},
    include_package_data=True,
    install_requires={requirements},
    description="Encrypted module loader for {package_name}",
    author="Auto Generator",
)
'''
setup_file = project_root / "setup.py"
setup_file.write_text(setup_code)

# --- 6. Build the wheel ---
print("📦 Building wheel package...")
subprocess.run(["python", "setup.py", "bdist_wheel"], cwd=project_root)

print("\n✅ Done! Your encrypted wheel is ready in:")
print(f"   {project_root / 'dist'}")
