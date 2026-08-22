
# AdminUsageDailyPoint

One day of aggregated usage for a (user, provider, model, source) bucket.

## Properties

Name | Type
------------ | -------------
`date` | string
`userId` | string
`username` | string
`providerKey` | string
`model` | string
`source` | string
`inputTokens` | number
`outputTokens` | number

## Example

```typescript
import type { AdminUsageDailyPoint } from ''

// TODO: Update the object below with actual values
const example = {
  "date": null,
  "userId": null,
  "username": null,
  "providerKey": null,
  "model": null,
  "source": null,
  "inputTokens": null,
  "outputTokens": null,
} satisfies AdminUsageDailyPoint

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as AdminUsageDailyPoint
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


