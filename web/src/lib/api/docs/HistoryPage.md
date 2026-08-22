
# HistoryPage

One page of replayable history events (newest first-page or older).

## Properties

Name | Type
------------ | -------------
`events` | Array&lt;string&gt;
`oldestLine` | number
`hasMore` | boolean
`source` | string
`turnBase` | number

## Example

```typescript
import type { HistoryPage } from ''

// TODO: Update the object below with actual values
const example = {
  "events": null,
  "oldestLine": null,
  "hasMore": null,
  "source": null,
  "turnBase": null,
} satisfies HistoryPage

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as HistoryPage
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


