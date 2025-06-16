#!/bin/bash
# Script para limpiar los archivos obsoletos del proyecto EliteDynamicsAPI
# después de la refactorización automática.

echo "--- Iniciando limpieza final del proyecto ---"

# Lista de archivos obsoletos a eliminar
files_to_delete=(
    "app/api/routes/dynamics_actions.py"
    "app/core/action_mapper.py"
    "refactor_final.py"
)

# Lista de directorios obsoletos a eliminar
dirs_to_delete=(
    "refactor_output"
)

# Bucle para eliminar archivos
echo "Buscando y eliminando archivos obsoletos..."
for file in "${files_to_delete[@]}"; do
    if [ -f "$file" ]; then
        rm "$file"
        echo "  -> Eliminado: $file"
    else
        echo "  -> No encontrado, se omite: $file"
    fi
done

# Bucle para eliminar directorios
echo "Buscando y eliminando directorios obsoletos..."
for dir in "${dirs_to_delete[@]}"; do
    if [ -d "$dir" ]; then
        rm -rf "$dir"
        echo "  -> Eliminado directorio: $dir"
    else
        echo "  -> No encontrado, se omite: $dir"
    fi
done

echo "--- ✅ Limpieza completada ---"
echo "El proyecto está listo para ser guardado en GitHub."