# AI Business Intelligence Copilot

## Live Demo

[Open the AI Business Intelligence Copilot](https://thanishkanaini-ai-business-intelligence-copilot.streamlit.app)

An interactive Business Intelligence application that combines Python, SQL, Streamlit, Plotly, and an LLM API to analyze sales data through dashboards, natural-language questions, and automated executive summaries.

## Key Features

- Interactive filtering by region, category, and year
- KPI tracking for sales, profit, profit margin, orders, and customers
- Regional, category, segment, product, customer, and monthly trend analysis
- Natural-language business questions converted into SQL
- AI-generated explanations of query results
- Filter-aware AI Business Intelligence Copilot
- Automated executive summaries with sales and profit growth
- Identification of top-performing products and weak-performing subcategories
- Data-driven management recommendations

## Tech Stack

- Python
- Pandas
- SQLite / SQL
- Streamlit
- Plotly
- OpenAI API

## How to Run the Project

1. Clone the repository.

2. Install the required packages:

```bash
pip install -r requirements.txt
```

3. Create a `.env` file in the project root.

4. Add your OpenAI API key:

```text
OPENAI_API_KEY=your_openai_api_key_here
```

5. Run the Streamlit application:

```bash
python -m streamlit run app.py
```

6. Open the local Streamlit URL shown in the terminal.