import sys
from .custom_loader import EncryptedModuleFinder
import os

key = os.environ.get("TABLE_CLASSIFIER_KEY")
iv = os.environ.get("TABLE_CLASSIFIER_IV")

if key is None or iv is None:
    raise ImportError("Encryption key/IV must be set in environment variables")

key = key.encode("utf-8")
iv = iv.encode("utf-8")

sys.meta_path.insert(0, EncryptedModuleFinder(key, iv))
