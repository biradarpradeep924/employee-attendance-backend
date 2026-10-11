# DECISIONS.md

### 1. Indexes

I added a unique index on `emp_code` in the `employees` collection to prevent duplicated employee codes. To ensure no employee can register attendance for a specific day twice, a unique compound index was created on `emp_code` and `date`. An index on `date` and `emp_code` was also added to make the process of attending listing easier. No indexes were tested and discarded yet.

### 2. Punch-in race

When there are two identical punch-in requests, both may want to insert a record at the same time. The unique compound index will allow creating a record only once for each employee and date. The second request will receive a duplicate-key error, and the API will return HTTP 409.

### 3. Ties in the leaderboard

The late leaderboard hasn't been implemented yet, so it is impossible to state how ties at the limit are handled. It should still follow the rules specified in the assignment's ranking and sorting.

### 4. Headcount

Department summary is also not implemented yet. It should include employees that have joined the company before the end of the selected period regardless of the attendance logging.

### 5. More data

To handle the growth of the data 100 times, I would check the queries' and indexes' performance using the increased dataset size.