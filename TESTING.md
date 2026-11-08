# Testing Documentation

## 1. Automated tests

The project uses pytest and GitHub Actions to run automated tests.

Latest test result:
- 14 tests passed
- 0 tests failed
- 9 analytics tests
- 5 assistant tests

## 2. Assistant test cases

Five assistant functions were tested:

| Test | Expected result | Result |
|---|---|---|
| Total revenue | Selects get_total | Passed |
| Annual revenue | Selects group_total by Year | Passed |
| Revenue by store type | Selects group_total by StoreType | Passed |
| Revenue by category | Selects group_total by Category | Passed |
| Data quality question | Selects data_quality_report | Passed |

## 3. Issue identified and fixed

During development, the assistant initially received the original Sales table instead of the prepared sales data.

This caused an error when asking questions about annual revenue because the Year column was not available.

## 4. Fix and retest

The issue was fixed by using analytics.prepare_sales_data() before passing the data to the assistant.

After the fix:
- The annual revenue question worked correctly.
- The assistant returned revenue for all five years.
- The five assistant tests passed.
- The complete automated test suite passed with 14 tests.

## 5. Automated testing

GitHub Actions runs pytest automatically when code is pushed to the main branch.

The successful test run is visible in the repository's Actions tab.
