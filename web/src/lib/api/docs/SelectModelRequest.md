
# SelectModelRequest


## Properties

Name | Type
------------ | -------------
`defaultModel` | string
`defaultThinking` | boolean
`restartRunningSessions` | boolean
`forceRestartBusySessions` | boolean

## Example

```typescript
import type { SelectModelRequest } from ''

// TODO: Update the object below with actual values
const example = {
  "defaultModel": null,
  "defaultThinking": null,
  "restartRunningSessions": null,
  "forceRestartBusySessions": null,
} satisfies SelectModelRequest

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as SelectModelRequest
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


