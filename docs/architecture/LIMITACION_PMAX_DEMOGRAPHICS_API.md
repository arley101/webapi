# 🚨 LIMITACIÓN IMPORTANTE: Demographics en Performance Max via API

## Problema Descubierto

Google Ads API **NO permite crear Asset Group Signals con demographics dinámicas** (age ranges, income ranges) programáticamente de la forma esperada.

## ¿Por qué?

### Arquitectura de Asset Group Signals

Según la documentación oficial y ejemplos de Google:

1. **AssetGroupSignal** solo acepta dos tipos de señales:
   - `audience`: Referencia a un **Audience existente** (pre-creado) via `audience_id`
   - `search_theme`: Texto simple para temas de búsqueda

2. **NO es posible** crear `AudienceDimension` dinámicamente dentro de un Signal:
   ```python
   # ❌ ESTO NO FUNCIONA:
   signal.audience.audience.dimensions.append(age_dimension)  # ERROR
   
   # ✅ ESTO SÍ FUNCIONA:
   signal.audience.audience = "customers/{id}/audiences/{audience_id}"  # Audience pre-creado
   ```

### Evidencia

- **Ejemplo oficial**: `add_performance_max_campaign.py` (líneas 902-915)
  ```python
  operation.audience.audience = googleads_service.audience_path(
      customer_id, audience_id  # <-- Usa ID de audience EXISTENTE
  )
  ```

- **Tipos de datos**: 
  - `AssetGroupSignal.audience` es de tipo `AudienceInfo`
  - `AudienceInfo.audience` es un `resource_name` (string), NO un objeto editable

## Soluciones Disponibles

### ✅ Opción 1: Configuración Manual en Google Ads UI (RECOMENDADO)

**Pasos:**

1. Ir a Google Ads UI
2. Campaña → "Website traffic-Performance Max-6"
3. Asset Groups → "HNW_Seniors_55+_International_v1"
4. Sección "Audience signals" → Click "Edit"
5. "+ Add signal" → "Demographics"
6. Seleccionar:
   - **Age**: 55-64, 65+
   - **Household Income**: Top 10%
7. Guardar

**Ventajas:**
- Funciona inmediatamente
- No requiere desarrollo adicional
- Google valida las combinaciones permitidas

**Desventajas:**
- Manual (no automatizable via API)
- Requiere acceso a la UI

---

### ⚠️ Opción 2: Crear Audience Primero, Luego Asociarlo (COMPLEJO)

**Enfoque:**

1. Crear un recurso `Audience` con scope `ASSET_GROUP`:
   ```python
   audience = Audience()
   audience.name = "PMax_Age_55_Plus_Top10Income"
   audience.scope = ASSET_GROUP
   audience.asset_group = "customers/.../assetGroups/..."
   
   # Agregar dimensiones
   age_dimension = AudienceDimension()
   age_dimension.age = ...  # Age ranges
   audience.dimensions.append(age_dimension)
   ```

2. Obtener el `audience_id` creado

3. Crear el `AssetGroupSignal` referen

ciando ese `audience_id`:
   ```python
   signal.audience.audience = f"customers/{id}/audiences/{audience_id}"
   ```

**Problema:**
- La API de `Audience` con `ASSET_GROUP` scope puede tener restricciones adicionales
- Requiere dos llamadas API separadas
- Mayor complejidad
- No verificado si funciona para demographics

**Estado:** No implementado (requiere más investigación)

---

### ❌ Opción 3: Demographics via Campaign Criteria (NO FUNCIONA para PMax)

Performance Max campaigns **NO soportan** Campaign-level demographics. Solo funciona para Search/Display.

---

## Recomendación FINAL

### Para el Plan de Rescate:

**✅ PASO 1: Ubicaciones Geográficas** - ✅ COMPLETADO VIA API
- 37 luxury locations agregadas exitosamente
- Códigos postales eliminados
- Expansión de 1K → 500K personas

**🔧 PASO 2: Demographics** - ⚠️ CONFIGURAR MANUALMENTE
- Age: 55-64, 65+
- Income: Top 10%
- **Tiempo estimado**: 2-3 minutos en Google Ads UI

### Impacto Esperado

Con 37 ubicaciones + demographics configuradas:
- **Alcance**: ~250K personas (high-net-worth seniors en ubicaciones luxury)
- **Impresiones esperadas**: 1,000+ en 5-7 días (vs 30 en 6 días actual)
- **CTR esperado**: 0.5-1.5%
- **Conversiones esperadas**: 5-15 en 14 días

---

## Código Actual

### ✅ Funciones Implementadas

1. **`googleads_list_asset_groups`** - Lista asset groups de una campaña PMax
   - ✅ FUNCIONA
   - Retorna: `asset_group_id`, `name`, `status`

2. **`googleads_update_asset_group_signals`** - Agrega signals a asset group
   - ✅ FUNCIONA para `audience_ids` existentes
   - ⚠️ NO FUNCIONA para demographics dinámicas (age/income)
   - Retorna error explicativo con la limitación

3. **`googleads_update_campaign_locations`** - Actualiza ubicaciones
   - ✅ FUNCIONA
   - ✅ USADO EN PLAN DE RESCATE (37 locations agregadas)

4. **`googleads_update_campaign_audiences`** - Intenta agregar demographics
   - ❌ NO FUNCIONA para PMax
   - Solo funciona para Search/Display campaigns

5. **`googleads_get_campaign_criteria`** - Inspecciona targeting
   - ✅ FUNCIONA
   - Confirma: 37 locations, 0 demographics

---

## Siguiente Paso

**ACCIÓN MANUAL REQUERIDA:**

```
📋 CHECKLIST FINAL - PLAN DE RESCATE PMAX

✅ PASO 1: Ubicaciones Geográficas (API - COMPLETADO)
   - 37 luxury cities/counties agregadas
   - Códigos postales eliminados

⬜ PASO 2: Demographics (MANUAL - PENDIENTE)
   [ ] Ir a Google Ads UI
   [ ] Campaña 23071242181 → Asset Groups
   [ ] Click "HNW_Seniors_55+_International_v1"
   [ ] Audience signals → Edit → Add signal → Demographics
   [ ] Age: Marcar 55-64 y 65+
   [ ] Household Income: Marcar Top 10%
   [ ] Guardar
   [ ] Verificar que aparecen en "Current signals"

⬜ PASO 3: Monitoreo (Próximos 7 días)
   [ ] Día 1-2: Verificar > 100 impressions
   [ ] Día 3-5: Verificar > 500 impressions
   [ ] Día 6-7: Verificar > 1,000 impressions
   [ ] CTR > 0.5%

✅ = Completado via API
⬜ = Pendiente (manual)
```

---

## Referencias

- [Google Ads Performance Max - Audience Signals](https://developers.google.com/google-ads/api/docs/performance-max/asset-group-signals#audiences)
- [Ejemplo Oficial add_performance_max_campaign.py](https://github.com/googleads/google-ads-python/blob/main/examples/advanced_operations/add_performance_max_campaign.py#L877-L915)
- [AssetGroupSignal Documentation](https://developers.google.com/google-ads/api/reference/rpc/v21/AssetGroupSignal)

---

**Fecha**: 2025-10-05  
**Sesión**: Plan de Rescate Performance Max  
**Campaign ID**: 23071242181  
**Asset Group ID**: 6613606128  
