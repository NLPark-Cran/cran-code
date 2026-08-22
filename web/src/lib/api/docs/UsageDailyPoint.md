
# UsageDailyPoint

One day of aggregated usage for a (provider, model, source) bucket.

## Properties

Name | Type
------------ | -------------
`date` | string
`providerKey` | string
`model` | string
`source` | string
`inputTokens` | number
`outputTokens` | number

## Example

```typescript
import type { UsageDailyPoint } from ''

// TODO: Update the object below with actual values
const example = {
  "date": null,
  "providerKey": null,
  "model": null,
  "source": null,
  "inputTokens": null,
  "outputTokens": null,
} satisfies UsageDailyPoint

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as UsageDailyPoint
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


