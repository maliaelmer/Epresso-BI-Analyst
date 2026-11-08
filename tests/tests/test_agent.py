import pandas as pd
import agent


def sample_data():
    return pd.DataFrame({
        "Revenue": [100, 200, 50, 150],
        "Year": [2025, 2025, 2026, 2026],
        "StoreType": ["Website", "Brick & Mortar", "Website", "Brick & Mortar"],
        "Category": ["Beans", "Machines", "Beans", "Machines"],
    })


def test_total_revenue_question():
    df = sample_data()
    answer = agent.answer_question("What is the total revenue?", df)

    assert "500" in answer["findings"]
    assert answer["tool_log"][0]["tool"] == "get_total"


def test_annual_revenue_question():
    df = sample_data()
    answer = agent.answer_question("What is the annual revenue by year?", df)

    assert answer["tool_log"][0]["tool"] == "group_total"
    assert "2025" in answer["findings"]
    assert "2026" in answer["findings"]


def test_store_type_question():
    df = sample_data()
    answer = agent.answer_question("What is the revenue by store type?", df)

    assert answer["tool_log"][0]["tool"] == "group_total"
    assert "Website" in answer["findings"]
    assert "Brick & Mortar" in answer["findings"]


def test_category_question():
    df = sample_data()
    answer = agent.answer_question("What is the revenue by product category?", df)

    assert answer["tool_log"][0]["tool"] == "group_total"
    assert "Beans" in answer["findings"]
    assert "Machines" in answer["findings"]


def test_data_quality_question():
    df = sample_data()
    answer = agent.answer_question("Are there missing values or duplicates?", df)

    assert answer["tool_log"][0]["tool"] == "data_quality_report"
