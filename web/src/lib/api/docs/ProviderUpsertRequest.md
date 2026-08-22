
# ProviderUpsertRequest


## Properties

Name | Type
------------ | -------------
`key` | string
`type` | string
`baseUrl` | string
`apiKey` | string
`models` | [Array&lt;ProviderModelSpec&gt;](ProviderModelSpec.md)
`customHeaders` | { [key: string]: string; }
`reasoningKey` | string

## Example

```typescript
import type { ProviderUpsertRequest } from ''

// TODO: Update the object below with actual values
const example = {
  "key": null,
  "type": null,
  "baseUrl": null,
  "apiKey": null,
  "models": null,
  "customHeaders": null,
  "reasoningKey": null,
} satisfies ProviderUpsertRequest

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as ProviderUpsertRequest
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


