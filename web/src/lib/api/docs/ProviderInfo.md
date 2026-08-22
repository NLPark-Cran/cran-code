
# ProviderInfo


## Properties

Name | Type
------------ | -------------
`key` | string
`type` | string
`baseUrl` | string
`hasApiKey` | boolean
`models` | [Array&lt;ProviderModelSpec&gt;](ProviderModelSpec.md)
`modelKeys` | Array&lt;string&gt;

## Example

```typescript
import type { ProviderInfo } from ''

// TODO: Update the object below with actual values
const example = {
  "key": null,
  "type": null,
  "baseUrl": null,
  "hasApiKey": null,
  "models": null,
  "modelKeys": null,
} satisfies ProviderInfo

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as ProviderInfo
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


