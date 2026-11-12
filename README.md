# E-Presso BI Analyst

## What this application does

The E-Presso BI Analyst is an interactive business intelligence application built with Python and Streamlit. It helps managers explore sales performance, compare revenue across years, store types and product categories, and investigate customer survey results. It also includes a rules-based assistant that answers business questions using approved analytical functions. The goal is to make business data easier to understand and support data-driven decisions.

## Live application

[Open the E-Presso BI Analyst](https://epreapp-bi-analyst-elaiq27a74x7ynvrfiqvhd.streamlit.app/)

The application may take a moment to start.

## How to use it

1. Open the live application.
2. Upload all five E-Presso data files using the sidebar:
   - Sales_EPresso.xlsx
   - Support_EX_B_Stores.csv
   - Products.xlsx
   - Categories_Espresso.xlsx
   - Support_EX_B_Survey.xlsx
3. Explore the **Data and profile** tab to review the tables, missing values and data types.
4. Use the **Dashboard** tab to filter revenue by year, category and store type.
5. Explore customer satisfaction and revenue in the **Survey Analysis** tab.
6. Ask business questions in the **Assistant** tab.

The survey data is read from the worksheet named `Survey Results`, with its column headings starting on row 3.

## Data model

The application uses five business tables:

| Table | Rows | Key / grain |
|---|---:|---|
| Sales | 25,200 | Sales ID; one store, product and month per record |
| Stores | 21 | Store ID |
| Products | 20 | Product ID |
| Categories | 5 | Category ID |
| Survey Results | 105 | Survey ID; one store and year per record |

### Relationships

- Sales[Store ID] → Stores[ID]
- Sales[Product ID] → Products[Product ID]
- Sales[Category ID] → Categories[Category ID]
- Survey Results[Store ID] → Stores[ID]

Survey Results is kept separate from the detailed Sales table to avoid multiplying sales records when combining data.

The application checks row counts and revenue totals before and after the sales table merges. These checks help identify unexpected dropped or duplicated records.

## Metric definitions

- **Total revenue:** Sum of the Revenue column.
- **Sales records:** Number of sales records in the filtered data.
- **Average revenue per record:** Total revenue divided by the number of sales records.
- **Revenue by year:** Sum of revenue grouped by year.
- **Revenue by store type:** Sum of revenue grouped by store type.
- **Revenue by category:** Sum of revenue grouped by product category.
- **Monthly revenue percentage:** Each calendar month's revenue as a percentage of revenue in the selected data.

Revenue is not profit. The data does not provide the costs needed to calculate profit or profit margins.

## Assistant

The application includes two answer modes:

- **Data-based:** Uses predefined rules to select the appropriate analytical function.
- **Gemini-assisted:** Uses Google's Gemini model to interpret the question and select an approved analytical function.

Both modes use Python functions to perform the actual calculations. Gemini helps interpret the question and choose the tool; it does not calculate or invent business figures.

The assistant can select from five approved analytical tools:

| Tool | Purpose |
|---|---|
| `get_total` | Calculates totals, such as total revenue, with optional filters |
| `group_total` | Groups revenue by year, store type or category |
| `revenue_growth_by_channel` | Calculates revenue growth by sales channel |
| `data_quality_report` | Checks missing values and duplicate rows |
| `get_average_satisfaction` | Calculates average customer satisfaction overall or by geographic region, with optional region filtering |

The assistant:
- Uses prepared sales and survey data from the uploaded files.
- Selects from a fixed list of approved tools.
- Validates tool names and arguments.
- Displays a tool-call log.
- Provides scope, findings and interpretation.
- Identifies the regions with the highest and lowest customer satisfaction.
- Rejects unsupported profit questions instead of incorrectly reporting revenue as profit.
- Allows a maximum of 15 questions per session.

It cannot execute arbitrary Python code, generate SQL queries or access unapproved analytical functions.

The Gemini API key is stored securely in Streamlit secrets and is not included in the GitHub repository.

## Validation

The application was compared against the provided Power BI report.

Five validation checks were completed:
- Total revenue: $42,174,440.
- Annual revenue for 2025–2029.
- Revenue by store type.
- Revenue by product category.
- Monthly revenue percentages.

All five comparisons matched the Power BI results.

An independent Excel check using `=SUM(G:G)` also returned $42,174,440.

### $1,000 modified-data test

A copy of the original Sales file was modified for testing.

- Sales ID: S0020250101
- Date: January 31, 2025
- Store: SH00 (Website)
- Original revenue: $6,780
- Modified revenue: $7,780
- Expected increase: $1,000

After uploading the modified file, the dashboard total increased from $42,174,440 to $42,175,440 without changing the application code or restarting it. The assistant and dashboard reflected the uploaded data. The original file was kept unchanged and restored afterward.

## Automated testing

The project uses pytest and GitHub Actions.

The latest successful automated test run included:
- 9 analytics tests.
- 5 assistant tests.
- 14 tests passed.
- 0 tests failed.

Tests run automatically when code is pushed to the main branch.

See `TESTING.md` for the testing documentation.

## Limitations

- Revenue is not profit.
- The application cannot calculate costs, profit margins or profitability.
- Survey results show customer satisfaction and interest, but do not establish why customers behave in a certain way.
- The assistant only supports questions covered by its approved rules and tools.
- The assistant has a 15-question session limit.
- Results depend on the accuracy and completeness of uploaded data.

## Project files

| File | Purpose |
|---|---|
| `streamlit_app.py` | Streamlit interface and user interaction |
| `analytics.py` | Data loading, calculations and analytical functions |
| `agent.py` | Rules-based assistant and tool validation |
| `tests/` | Automated analytics and assistant tests |
| `TESTING.md` | Testing documentation |
| `requirements.txt` | Application dependencies |
| `requirements-dev.txt` | Development and testing dependencies |

## Run it locally

Install the dependencies:

```bash
pip install -r requirements-dev.txt
```

Start the application:

```bash
streamlit run streamlit_app.py
```

Run the automated tests:

```bash
python -m pytest
```

## Secrets

Never commit API keys, passwords or other private credentials to GitHub.
