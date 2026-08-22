
# GitCommitResponse


## Properties

Name | Type
------------ | -------------
`hash` | string
`shortHash` | string
`message` | string
`author` | string
`date` | string

## Example

```typescript
import type { GitCommitResponse } from ''

// TODO: Update the object below with actual values
const example = {
  "hash": null,
  "shortHash": null,
  "message": null,
  "author": null,
  "date": null,
} satisfies GitCommitResponse

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as GitCommitResponse
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


