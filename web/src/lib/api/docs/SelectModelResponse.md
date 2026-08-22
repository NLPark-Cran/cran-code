
# SelectModelResponse


## Properties

Name | Type
------------ | -------------
`defaultModel` | string
`defaultThinking` | boolean
`restartedSessionIds` | Array&lt;string&gt;
`skippedBusySessionIds` | Array&lt;string&gt;

## Example

```typescript
import type { SelectModelResponse } from ''

// TODO: Update the object below with actual values
const example = {
  "defaultModel": null,
  "defaultThinking": null,
  "restartedSessionIds": null,
  "skippedBusySessionIds": null,
} satisfies SelectModelResponse

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as SelectModelResponse
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


