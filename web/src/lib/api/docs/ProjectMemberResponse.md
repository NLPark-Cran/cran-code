
# ProjectMemberResponse


## Properties

Name | Type
------------ | -------------
`id` | string
`userId` | string
`username` | string
`displayName` | string
`role` | string
`joinedAt` | string

## Example

```typescript
import type { ProjectMemberResponse } from ''

// TODO: Update the object below with actual values
const example = {
  "id": null,
  "userId": null,
  "username": null,
  "displayName": null,
  "role": null,
  "joinedAt": null,
} satisfies ProjectMemberResponse

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as ProjectMemberResponse
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


