#!/usr/bin/env python3
"""
🚀 ACTIVADOR DE INTEGRACIONES - ELITE DYNAMICS AI
===============================================

Activa WhatsApp y/o Teams cuando estés listo.
"""

import os
import shutil
import json

def activate_whatsapp():
    """Activar integración de WhatsApp"""
    print("📱 Activando WhatsApp Business...")
    
    # Verificar credenciales
    env_file = "integrations_ready/.env.whatsapp.template"
    if not os.path.exists(env_file):
        print("❌ Template de .env no encontrado")
        return False
    
    # Leer template
    with open(env_file, 'r') as f:
        content = f.read()
    
    # Verificar si las credenciales están configuradas
    if "tu_token_de_meta_aqui" in content:
        print("⚠️ Necesitas configurar las credenciales primero:")
        print("1. Edita integrations_ready/.env.whatsapp.template")
        print("2. Reemplaza 'tu_token_de_meta_aqui' con tu token real")
        print("3. Reemplaza 'tu_phone_id_aqui' con tu phone ID real")
        print("4. Vuelve a ejecutar este script")
        return False
    
    # Copiar archivos de integración
    files_to_copy = [
        "whatsapp_integration_complete.py",
        "whatsapp_config.json"
    ]
    
    for file in files_to_copy:
        src = f"integrations_ready/{file}"
        if os.path.exists(src):
            shutil.copy2(src, file)
            print(f"   ✅ {file} activado")
    
    # Copiar .env configurado
    shutil.copy2(env_file, ".env")
    print("   ✅ Variables de entorno configuradas")
    
    # Actualizar main.py
    print("   🔧 Actualizando main.py para incluir WhatsApp...")
    update_main_for_whatsapp()
    
    print("\n🎉 ¡WhatsApp Business activado!")
    print("💡 Ejecuta: python main.py para probar")
    return True

def activate_teams():
    """Activar integración de Teams"""
    print("👥 Activando Microsoft Teams...")
    
    # Similar lógica para Teams
    files_to_copy = [
        "teams_integration_complete.py",
        "teams_config.json",
        "teams_manifest.json"
    ]
    
    for file in files_to_copy:
        src = f"integrations_ready/{file}"
        if os.path.exists(src):
            shutil.copy2(src, file)
            print(f"   ✅ {file} activado")
    
    print("\n🎉 ¡Microsoft Teams activado!")
    return True

def update_main_for_whatsapp():
    """Actualizar main.py para incluir rutas de WhatsApp"""
    # Leer main.py actual
    if not os.path.exists("main.py"):
        print("   ⚠️ main.py no encontrado")
        return
    
    with open("main.py", 'r') as f:
        content = f.read()
    
    # Agregar importación de WhatsApp si no existe
    whatsapp_import = "from whatsapp_integration_complete import whatsapp_bp"
    whatsapp_register = "app.register_blueprint(whatsapp_bp)"
    
    if whatsapp_import not in content:
        # Buscar donde agregar la importación
        if "from flask import" in content:
            content = content.replace(
                "from flask import",
                f"{whatsapp_import}\nfrom flask import"
            )
        
        # Buscar donde registrar el blueprint
        if "if __name__ == '__main__':" in content:
            content = content.replace(
                "if __name__ == '__main__':",
                f"{whatsapp_register}\n\nif __name__ == '__main__':"
            )
    
    # Guardar main.py actualizado
    with open("main.py", 'w') as f:
        f.write(content)

def main():
    """Función principal"""
    print("🚀 ACTIVADOR DE INTEGRACIONES ELITE DYNAMICS AI")
    print("=" * 50)
    
    print("\nOpciones disponibles:")
    print("1. 📱 Activar WhatsApp Business")
    print("2. 👥 Activar Microsoft Teams") 
    print("3. 🚀 Activar ambas")
    print("4. ❌ Salir")
    
    choice = input("\n¿Qué quieres activar? (1-4): ")
    
    if choice == "1":
        activate_whatsapp()
    elif choice == "2":
        activate_teams()
    elif choice == "3":
        activate_whatsapp()
        activate_teams()
    elif choice == "4":
        print("👋 ¡Hasta luego!")
    else:
        print("❌ Opción inválida")

if __name__ == "__main__":
    main()
