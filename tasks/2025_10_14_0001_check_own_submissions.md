# Check one's own submissions

Add the following route:

## GET /users/@me/submissions

Query parameters:

```typescript
interface {
    type: 'map' | 'completion'  // Default: map
    page: number  // Default: 1
    status: 'pending' | 'all'  // Default: all
}
```

Return type:

```typescript
interface {
    pages: number
    total: number  // Total number of records
    data: MapSubmission | CompletionSubmission  // The completion submission includes the map's partial data.
}
```

This route returns a paginated view of the user's submissions (map or completions, depending on the type parameter). Include 50 records per page.

## Tests

1. Find a user with no map submissions and test that it returns an empty array
2. Get the route of a user where you know beforehand how many map submissions it has. Check that pages and total match, and check the return schema of `data`
3. Assert that an invalid type results in a 422 response
4. Assert that a non-numeric page results in a 422 response
5. Assert that a negative or 0 page results in a 422 response
6. Assert that an invalid status results in a 422 response
7. Redo test 1 but with completion submissions.
8. Redo test 2 but with completion submissions.

To do test 1 and 7, you can use the POST routes to submit maps as a new user, if you want. To get a user with **A LOT** of submissions for tests 2 and 8,
