targetScope = 'subscription'

@minLength(1)
@maxLength(64)
@description('Nombre del entorno')
param environmentName string

@minLength(1)
@description('Ubicación principal de los recursos')
param location string

param resourceGroupName string = ''

// Variables principales
var abbrs = loadJsonContent('./abbreviations.json')
var resourceToken = toLower(uniqueString(subscription().id, environmentName, location))
var tags = { 'azd-env-name': environmentName }

// Crear grupo de recursos
resource rg 'Microsoft.Resources/resourceGroups@2021-04-01' = {
  name: !empty(resourceGroupName) ? resourceGroupName : '${abbrs.resourcesResourceGroups}${environmentName}'
  location: location
  tags: tags
}

// Desplegar la infraestructura principal
module resources 'resources.bicep' = {
  name: 'resources'
  scope: rg
  params: {
    environmentName: environmentName
    location: location
    resourceToken: resourceToken
    tags: tags
  }
}

// Outputs
output AZURE_LOCATION string = location
output AZURE_TENANT_ID string = tenant().tenantId
output AZURE_RESOURCE_GROUP string = rg.name

// App Service outputs
output AZURE_APP_SERVICE_ENDPOINT string = resources.outputs.AZURE_APP_SERVICE_ENDPOINT
output AZURE_APP_SERVICE_NAME string = resources.outputs.AZURE_APP_SERVICE_NAME

// Log Analytics outputs
output AZURE_LOG_ANALYTICS_WORKSPACE_NAME string = resources.outputs.AZURE_LOG_ANALYTICS_WORKSPACE_NAME
