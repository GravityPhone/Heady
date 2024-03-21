import pkgutil
import importlib

package_name = 'openai'  # Replace with the actual library name

package = importlib.import_module(package_name)

for importer, modname, ispkg in pkgutil.iter_modules(package.__path__, prefix=package_name + '.'):
    # Check if modname already starts with package_name to avoid duplication
    full_modname = modname if modname.startswith(package_name) else f"{package_name}.{modname}"
    print(f"Found submodule {modname} (is a package: {ispkg})")
    try:
        module = importlib.import_module(full_modname)
        print(dir(module))  # Lists all attributes of the module, including callable methods
    except ModuleNotFoundError as e:
        print(f"Could not import {full_modname}: {e}")
