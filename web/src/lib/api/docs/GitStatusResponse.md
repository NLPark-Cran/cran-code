
# GitStatusResponse


## Properties

Name | Type
------------ | -------------
`branch` | string
`ahead` | number
`behind` | number
`modified` | Array&lt;string&gt;
`staged` | Array&lt;string&gt;
`untracked` | Array&lt;string&gt;
`clean` | boolean

## Example

```typescript
import type { GitStatusResponse } from ''

// TODO: Update the object below with actual values
const example = {
  "branch": null,
  "ahead": null,
  "behind": null,
  "modified": null,
  "staged": null,
  "untracked": null,
  "clean": null,
} satisfies GitStatusResponse

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as GitStatusResponse
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


