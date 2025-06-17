# fix_actions_async.py
import os
import logging

logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

ACTIONS_DIR = 'app/actions'

def make_actions_async():
    logger.info("--- Iniciando Script de Reparación Asíncrona ---")
    
    # Obtenemos la lista de todos los archivos de acciones, excepto __init__.py
    try:
        action_files = [f for f in os.listdir(ACTIONS_DIR) if f.endswith('_actions.py')]
        logger.info(f"Se encontraron {len(action_files)} archivos de acciones para procesar.")
    except FileNotFoundError:
        logger.error(f"FATAL: El directorio '{ACTIONS_DIR}' no fue encontrado. Asegúrate de ejecutar el script desde la raíz del proyecto.")
        return

    total_files_modified = 0
    total_functions_modified = 0

    for filename in action_files:
        filepath = os.path.join(ACTIONS_DIR, filename)
        
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        new_lines = []
        file_modified = False
        functions_in_file_modified = 0
        
        for line in lines:
            new_line = line
            # Si la línea define una función que usa el cliente, la convierte en async
            if 'def ' in line and '(client: AuthenticatedHttpClient' in line:
                new_line = line.replace('def ', 'async def ', 1)
                functions_in_file_modified += 1
                total_functions_modified += 1
                file_modified = True
            
            # Si la línea contiene una llamada a un método del cliente, le añade await
            if 'client.request(' in line:
                if 'await' not in line:
                    new_line = line.replace('client.request(', 'await client.request(', 1)
                    file_modified = True

            new_lines.append(new_line)

        if file_modified:
            logger.info(f"Modificando archivo: {filename} ({functions_in_file_modified} funciones convertidas a async)")
            with open(filepath, 'w', encoding='utf-8') as f:
                f.writelines(new_lines)
            total_files_modified += 1

    logger.info("\n--- ✅ Proceso de Reparación Completado ---")
    logger.info(f"Archivos modificados: {total_files_modified}")
    logger.info(f"Funciones totales convertidas a async: {total_functions_modified}")

if __name__ == "__main__":
    make_actions_async()