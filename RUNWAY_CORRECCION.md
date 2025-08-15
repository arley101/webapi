# 🔧 CORRECCIÓN RUNWAY ML - VARIABLE DE ENTORNO

## ❌ PROBLEMA IDENTIFICADO
La variable de entorno para Runway ML estaba mal configurada.

### 🏷️ NOMBRE INCORRECTO (ACTUAL):
```
RUNWAY_API_KEY
```

### ✅ NOMBRE CORRECTO (SEGÚN DOCUMENTACIÓN OFICIAL):
```
RUNWAYML_API_SECRET
```

## 🔄 ACCIONES REQUERIDAS

### 1. **ACTUALIZAR EN AZURE APP SERVICE**

#### Ir a Azure Portal:
1. Abrir Azure Portal
2. Ir a App Service → `elitedynamicsapi`
3. En el menú lateral: **Configuration** → **Application Settings**

#### Actualizar Variable:
- **OPCIÓN A (Recomendada)**: Agregar nueva variable
  - **Name**: `RUNWAYML_API_SECRET`
  - **Value**: `key_e1e7c3c6c2136fd7ee70d0580ec923b6a0c76308bb178a6cd38a90adcf1227aebaf2180c8a6431e094bba74dd3dcffac5f8ee0e553518babdbc1767ba62fe56a`

- **OPCIÓN B**: Mantener ambas (compatible)
  - Mantener: `RUNWAY_API_KEY` (existente)
  - Agregar: `RUNWAYML_API_SECRET` (nuevo)

#### Guardar y Reiniciar:
1. Clic en **Save**
2. Esperar confirmación
3. **Restart** el App Service

### 2. **VERIFICAR CONFIGURACIÓN**

Después del reinicio, probar:
```bash
curl -X POST https://elitedynamicsapi.azurewebsites.net/api/v1/dynamics \
  -H "Content-Type: application/json" \
  -d '{"action": "runway_check_configuration", "params": {}}'
```

**Resultado esperado:**
```json
{
  "status": "success",
  "configuration": {
    "api_key_configured": true,
    "api_key_source": "environment (RUNWAYML_API_SECRET)",
    "recommended_var": "RUNWAYML_API_SECRET"
  },
  "ready": true
}
```

### 3. **PROBAR GENERACIÓN REAL**

Una vez configurado correctamente:
```bash
curl -X POST https://elitedynamicsapi.azurewebsites.net/api/v1/dynamics \
  -H "Content-Type: application/json" \
  -d '{
    "action": "runway_generate_video",
    "params": {
      "prompt": "Un gato corriendo por la playa",
      "model": "gen3a_turbo"
    }
  }'
```

## 📋 CAMBIOS REALIZADOS EN EL CÓDIGO

### ✅ ARCHIVO ACTUALIZADO: `app/actions/runway_actions.py`

1. **Función `_get_headers()`**:
   - Ahora busca: `RUNWAYML_API_SECRET`, `RUNWAYML_API_TOKEN`, `RUNWAY_API_KEY`
   - Prioriza nombres oficiales

2. **Función `runway_check_configuration()`**:
   - Detecta automáticamente la variable correcta
   - Reporta cuál está usando
   - Recomienda `RUNWAYML_API_SECRET`

### ✅ ARCHIVO ACTUALIZADO: `.env` (Local)
- Agregada variable `RUNWAYML_API_SECRET`
- Mantenida `RUNWAY_API_KEY` para compatibilidad

## 🎯 PRÓXIMOS PASOS

1. **INMEDIATO**: Actualizar variable en Azure
2. **VERIFICAR**: Probar configuración
3. **CONFIRMAR**: Generar video de prueba
4. **DOCUMENTAR**: Actualizar manual del asistente

## 📖 REFERENCIA OFICIAL

Según la documentación de Runway ML API:
- **Variable oficial**: `RUNWAYML_API_SECRET`
- **Formato header**: `Authorization: Bearer {api_key}`
- **Base URL**: `https://api.runwayml.com/v1`

---

**⚠️ IMPORTANTE**: Después de actualizar en Azure, el sistema funcionará correctamente para generar videos reales con Runway ML.
