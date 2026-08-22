
# UsageSummary


## Properties

Name | Type
------------ | -------------
`providerKey` | string
`source` | string
`inputTokens` | number
`outputTokens` | number
`totalTokens` | number
`quotaTokens` | number
`remainingTokens` | number

## Example

```typescript
import type { UsageSummary } from ''

// TODO: Update the object below with actual values
const example = {
  "providerKey": null,
  "source": null,
  "inputTokens": null,
  "outputTokens": null,
  "totalTokens": null,
  "quotaTokens": null,
  "remainingTokens": null,
} satisfies UsageSummary

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as UsageSummary
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


