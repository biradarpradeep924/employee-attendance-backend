# REVIEW.md

## Issues I found

While working on the starter code, I found the following issues and missing parts.

| # | Where | What was the issue? | How I noticed it | Fix / Status |
|---|---|---|---|---|
| 1 | Punch-out endpoint | The punch-in time from MongoDB was timezone-naive, but the current time was timezone-aware. Subtracting them caused an error. | The punch-out API returned a 500 error. | Converted the stored punch-in time to IST before calculating the duration. |
| 2 | GET `/attendance` | The timestamps are returned as datetime strings instead of epoch milliseconds. | Checked the response in Swagger UI. | Identified, but the fix is still pending. |
| 3 | App initialization | There are duplicate MongoDB imports and FastAPI app declarations in the current code. | Noticed while reviewing `main.py`. | Cleanup is pending. |
| 4 | MongoDB startup | The application logs database or index errors but may continue starting. | This can be checked by starting the app with an invalid MongoDB URI. | Needs better error handling. |
| 5 | Employee input validation | Some employee fields accept plain strings without enough validation. | Invalid or empty values may pass the initial validation. | More validation is needed. |
| 6 | Attendance regularization | The PATCH endpoint is not implemented yet. | The required request cannot be handled by the current code. | Not implemented yet. |
| 7 | Monthly employee analytics | The monthly analytics endpoint is missing. | The required endpoint is not available. | Not implemented yet. |
| 8 | Department summary | The department summary endpoint is missing. | The required endpoint is not available. | Not implemented yet. |
| 9 | Late leaderboard | The leaderboard endpoint is missing. | The required endpoint is not available. | Not implemented yet. |
| 10 | Department trend | The department trend endpoint is missing. | The required endpoint is not available. | Not implemented yet. |
| 11 | Admin explain endpoint | The endpoint for checking MongoDB aggregation execution plans is missing. | The required endpoint is not available. | Not implemented yet. |

## Things that I checked and kept

- **Separate collections:** I kept employees and attendance logs in separate collections because an employee can have multiple attendance records.
- **Unique employee code:** The unique index prevents two employees from having the same employee code.
- **Unique attendance record:** The compound unique index prevents duplicate records for the same employee and date.
- **Duplicate punch-in response:** Returning HTTP 409 when an attendance record already exists is appropriate.
- **Unknown employee:** Returning HTTP 404 when an employee does not exist is appropriate.
- **Pagination:** Pagination limits the number of records returned in one request.

## Current status

The basic employee and attendance APIs are working for the cases I tested. However, several required endpoints and some validation and timestamp fixes are still pending. I need to complete these parts and test the remaining business rules before submitting the assignment.