# validate_action_map.py
import importlib
import inspect
from typing import List
from app.core import action_mapper

def validate_action_map() -> bool:
    errors: List[str] = []
    print(f"🔍 Validando {len(action_mapper.ACTION_MAP)} acciones en ACTION_MAP...\n")

    for name, func in action_mapper.ACTION_MAP.items():
        if not callable(func):
            errors.append(f"❌ '{name}' no es callable.")
            continue

        try:
            module_name = func.__module__
            mod = importlib.import_module(module_name)
            real_func = getattr(mod, func.__name__)
            if not inspect.isfunction(real_func):
                errors.append(f"⚠️ '{name}' está definido, pero no es una función válida en {module_name}.")
        except Exception as e:
            errors.append(f"❌ Error al importar función '{name}': {e}")

    if errors:
        print(f"\n❌ Validación completada con {len(errors)} errores:\n")
        for error in errors:
            print(error)
        return False
    else:
        print("✅ Todas las acciones están correctamente mapeadas y listas para usar.")
        return True


def main():
    is_valid = validate_action_map()
    exit(0 if is_valid else 1)


if __name__ == "__main__":
    main()