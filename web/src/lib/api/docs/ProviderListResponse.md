
# ProviderListResponse


## Properties

Name | Type
------------ | -------------
`defaultModel` | string
`defaultThinking` | boolean
`providers` | [Array&lt;ProviderInfo&gt;](ProviderInfo.md)

## Example

```typescript
import type { ProviderListResponse } from ''

// TODO: Update the object below with actual values
const example = {
  "defaultModel": null,
  "defaultThinking": null,
  "providers": null,
} satisfies ProviderListResponse

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as ProviderListResponse
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


