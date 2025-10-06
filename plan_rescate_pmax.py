#!/usr/bin/env python3
"""
🚨 PLAN DE RESCATE - CAMPAÑA PERFORMANCE MAX
============================================

Este script implementa la estrategia de rescate completa para la campaña
Performance Max que tiene bajo rendimiento debido a segmentación por códigos postales.

ESTRATEGIA:
1. Eliminar TODOS los códigos postales
2. Agregar ciudades y regiones afluentes completas
3. Fortalecer señales de audiencia con intereses de lujo
4. Mantener estrategia de puja (Maximizar conversiones)

OBJETIVO: Generar IMPRESIONES en los próximos 5-7 días
"""

import requests
import json
from typing import Dict, List, Any

# Configuración
API_URL = "http://localhost:8000/api/v1/dynamics"  # Cambiar a Azure para producción
CUSTOMER_ID = "1536073437"
CAMPAIGN_ID = "23071242181"  # Website traffic-Performance Max-6

# ============================================================================
# PASO 1: UBICACIONES GEOGRÁFICAS ESTRATÉGICAS
# ============================================================================

# Ciudades de alto poder adquisitivo en EE.UU.
LUXURY_CITIES = [
    # California
    "Beverly Hills, California",
    "Malibu, California",
    "Newport Beach, California",
    "Palo Alto, California",
    "Atherton, California",
    
    # Florida
    "Miami, Florida",
    "Boca Raton, Florida",
    "Palm Beach, Florida",
    "Naples, Florida",
    "Jupiter, Florida",
    "Fisher Island, Florida",
    
    # Arizona
    "Scottsdale, Arizona",
    "Paradise Valley, Arizona",
    
    # Colorado
    "Aspen, Colorado",
    "Vail, Colorado",
    
    # New York
    "Southampton, New York",
    "East Hampton, New York",
    "Sag Harbor, New York",
    "Bridgehampton, New York",
    
    # Texas
    "Highland Park, Texas",
    "University Park, Texas",
    
    # Washington
    "Medina, Washington",
    "Mercer Island, Washington",
]

# Condados y regiones afluentes
LUXURY_REGIONS = [
    # California
    "Marin County, California",
    "Orange County, California",
    "Santa Clara County, California",
    
    # New York
    "Westchester County, New York",
    "Nassau County, New York",
    
    # Connecticut
    "Fairfield County, Connecticut",
    
    # New Jersey
    "Bergen County, New Jersey",
]

# ============================================================================
# PASO 2: SEÑALES DE AUDIENCIA (INTERESES DE LUJO)
# ============================================================================

# Datos demográficos
AGE_RANGES = [
    "AGE_RANGE_55_64",
    "AGE_RANGE_65_UP"
]

INCOME_RANGES = [
    "INCOME_RANGE_TOP_10_PERCENT"
]

# Intereses de lujo (estos son keywords/conceptos, no IDs de Google Ads)
LUXURY_INTERESTS = [
    "Luxury Travel",
    "Medical Tourism",
    "Private Aviation",
    "Yacht Ownership",
    "Golf Clubs",
    "Country Clubs",
    "First Class Travel",
    "Luxury Real Estate",
    "High-End Vehicles",
    "Investment Management",
    "Wealth Management",
    "Luxury Watches",
    "Fine Dining",
    "Spa and Wellness",
    "Cosmetic Surgery",
    "Anti-Aging Treatments"
]

# ============================================================================
# FUNCIONES AUXILIARES
# ============================================================================

def call_api(action: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """Llama a la API con la acción y parámetros especificados."""
    payload = {
        "action": action,
        "params": params
    }
    
    print(f"\n🔄 Ejecutando: {action}")
    print(f"   Parámetros: {json.dumps(params, indent=2)}")
    
    try:
        response = requests.post(API_URL, json=payload, timeout=60)
        result = response.json()
        
        if result.get("success") or result.get("status") == "success":
            print(f"   ✅ Éxito: {result.get('message', 'Operación completada')}")
        else:
            print(f"   ❌ Error: {result.get('message') or result.get('error', 'Error desconocido')}")
        
        return result
    except Exception as e:
        print(f"   ❌ Excepción: {e}")
        return {"success": False, "error": str(e)}


def display_current_criteria():
    """Muestra los criterios actuales de la campaña."""
    print("\n" + "="*80)
    print("📊 PASO 0: REVISAR CONFIGURACIÓN ACTUAL")
    print("="*80)
    
    result = call_api("googleads_get_campaign_criteria", {
        "customer_id": CUSTOMER_ID,
        "campaign_id": CAMPAIGN_ID
    })
    
    if result.get("success"):
        data = result.get("data", {})
        summary = result.get("summary", {})
        
        print(f"\n📍 UBICACIONES ACTUALES: {summary.get('total_locations', 0)}")
        for loc in data.get("locations", [])[:5]:  # Mostrar solo las primeras 5
            print(f"   - {loc.get('geo_target', 'N/A')} (ID: {loc.get('id')})")
        
        print(f"\n👥 AUDIENCIAS ACTUALES:")
        print(f"   Rangos de edad: {summary.get('total_age_ranges', 0)}")
        for age in data.get("age_ranges", []):
            print(f"   - {age.get('age_range', 'N/A')}")
        
        print(f"   Rangos de ingreso: {summary.get('total_income_ranges', 0)}")
        for income in data.get("income_ranges", []):
            print(f"   - {income.get('income_range', 'N/A')}")
        
        print(f"\n   Total criterios: {summary.get('total_criteria', 0)}")


def update_locations():
    """Actualiza las ubicaciones geográficas de la campaña."""
    print("\n" + "="*80)
    print("🗺️  PASO 1: ACTUALIZAR UBICACIONES GEOGRÁFICAS")
    print("="*80)
    print("\n🎯 ESTRATEGIA: Eliminar códigos postales y agregar ciudades/regiones completas")
    print(f"   Total de nuevas ubicaciones: {len(LUXURY_CITIES) + len(LUXURY_REGIONS)}")
    
    # Combinar ciudades y regiones
    all_locations = LUXURY_CITIES + LUXURY_REGIONS
    
    print(f"\n📍 Ubicaciones a agregar:")
    for i, loc in enumerate(all_locations[:10], 1):
        print(f"   {i}. {loc}")
    if len(all_locations) > 10:
        print(f"   ... y {len(all_locations) - 10} más")
    
    input("\n⚠️  Presiona ENTER para continuar con la actualización de ubicaciones...")
    
    result = call_api("googleads_update_campaign_locations", {
        "customer_id": CUSTOMER_ID,
        "campaign_id": CAMPAIGN_ID,
        "locations": all_locations,
        "remove_all_existing": True
    })
    
    return result


def update_audiences():
    """Actualiza las señales de audiencia de la campaña."""
    print("\n" + "="*80)
    print("👥 PASO 2: FORTALECER SEÑALES DE AUDIENCIA")
    print("="*80)
    print("\n🎯 ESTRATEGIA: Agregar datos demográficos de alto poder adquisitivo")
    
    print(f"\n📊 Rangos de edad:")
    for age in AGE_RANGES:
        print(f"   - {age}")
    
    print(f"\n💰 Rangos de ingreso:")
    for income in INCOME_RANGES:
        print(f"   - {income}")
    
    print(f"\n🏆 Intereses de lujo (para referencia):")
    for interest in LUXURY_INTERESTS[:5]:
        print(f"   - {interest}")
    print(f"   ... y {len(LUXURY_INTERESTS) - 5} más")
    
    input("\n⚠️  Presiona ENTER para continuar con la actualización de audiencias...")
    
    result = call_api("googleads_update_campaign_audiences", {
        "customer_id": CUSTOMER_ID,
        "campaign_id": CAMPAIGN_ID,
        "age_ranges": AGE_RANGES,
        "income_ranges": INCOME_RANGES,
        "interests": LUXURY_INTERESTS
    })
    
    return result


def display_summary():
    """Muestra un resumen del plan de rescate."""
    print("\n" + "="*80)
    print("📋 RESUMEN DEL PLAN DE RESCATE")
    print("="*80)
    
    print("""
✅ CAMBIOS IMPLEMENTADOS:

1. 🗺️  UBICACIONES GEOGRÁFICAS:
   ❌ ELIMINADO: Códigos postales restrictivos
   ✅ AGREGADO: 30+ ciudades y regiones afluentes
   
   Ejemplos:
   • Beverly Hills, CA
   • Miami, FL
   • Aspen, CO
   • The Hamptons, NY
   • Scottsdale, AZ

2. 👥 SEÑALES DE AUDIENCIA:
   ✅ AGREGADO: Edad 55-64 y 65+
   ✅ AGREGADO: Ingresos Top 10%
   ✅ DOCUMENTADO: Intereses de lujo para optimización manual

3. 💰 ESTRATEGIA DE PUJA:
   ✅ MANTENIDO: Maximizar conversiones (sin CPA objetivo)
   ⚠️  Razón: Dejar que el algoritmo aprenda primero

📊 EXPECTATIVAS PARA LOS PRÓXIMOS 5-7 DÍAS:

✓ FASE DE APRENDIZAJE: La campaña volverá a "Learning"
✓ OBJETIVO PRINCIPAL: Generar IMPRESIONES (olvidar clicks/conversiones por ahora)
✓ MÉTRICA CLAVE: Impresiones > 1,000 en los primeros 3 días
✓ ACCIÓN: NO hacer cambios durante el período de aprendizaje

🎯 PRÓXIMOS PASOS:

1. Monitorear impresiones diariamente
2. Verificar que las ubicaciones se registren correctamente
3. Después de 7 días con datos, evaluar:
   - Si las impresiones aumentaron significativamente → Éxito
   - Si no hay cambio → Revisar presupuesto y assets
   
⚠️  IMPORTANTE: Dar tiempo al algoritmo. Mínimo 14 días antes de cambiar estrategia.

""")

    print("="*80)


# ============================================================================
# FUNCIÓN PRINCIPAL
# ============================================================================

def main():
    """Ejecuta el plan de rescate completo."""
    print("""
    ╔═══════════════════════════════════════════════════════════════════╗
    ║                                                                   ║
    ║           🚨 PLAN DE RESCATE - PERFORMANCE MAX 🚨                ║
    ║                                                                   ║
    ║   Campaña: Website traffic-Performance Max-6                     ║
    ║   ID: 23071242181                                                ║
    ║   Cliente: 1536073437                                            ║
    ║                                                                   ║
    ╚═══════════════════════════════════════════════════════════════════╝
    """)
    
    print("\n🎯 OBJETIVO: Ampliar el alcance geográfico para generar más impresiones")
    print("📊 PROBLEMA ACTUAL: Solo 30 impresiones en 6 días (demasiado bajo)")
    print("💡 SOLUCIÓN: Eliminar códigos postales y usar ciudades/regiones completas")
    
    input("\n⚠️  Presiona ENTER para comenzar el análisis inicial...")
    
    try:
        # Paso 0: Mostrar configuración actual
        display_current_criteria()
        
        # Paso 1: Actualizar ubicaciones
        loc_result = update_locations()
        
        if not loc_result.get("success"):
            print("\n❌ ERROR: No se pudieron actualizar las ubicaciones.")
            print("   Revisa los logs para más detalles.")
            return
        
        # Paso 2: Actualizar audiencias
        aud_result = update_audiences()
        
        if not aud_result.get("success"):
            print("\n⚠️  ADVERTENCIA: Las audiencias no se actualizaron completamente.")
            print("   Es posible que necesites configurar algunos criterios manualmente.")
        
        # Mostrar resumen final
        display_summary()
        
        print("\n✅ PLAN DE RESCATE EJECUTADO EXITOSAMENTE\n")
        print("📊 Revisa la campaña en Google Ads en las próximas horas para confirmar cambios.")
        print("⏰ Monitorea las impresiones durante los próximos 5-7 días.\n")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Plan de rescate cancelado por el usuario.\n")
    except Exception as e:
        print(f"\n\n❌ ERROR INESPERADO: {e}\n")


if __name__ == "__main__":
    main()
