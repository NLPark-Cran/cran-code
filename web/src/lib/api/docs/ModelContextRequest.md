
# ModelContextRequest

Set a model\'s context window size.  K3 example: 262144 (Moderato) / 524288 / 1048576 (Allegretto+ 1M). The usable ceiling depends on the subscription tier of the account behind the provider key.

## Properties

Name | Type
------------ | -------------
`maxContextSize` | number
`restartRunningSessions` | boolean

## Example

```typescript
import type { ModelContextRequest } from ''

// TODO: Update the object below with actual values
const example = {
  "maxContextSize": null,
  "restartRunningSessions": null,
} satisfies ModelContextRequest

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as ModelContextRequest
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


