import streamlit as st
import pandas as pd
import openai
from datetime import datetime

# ---------------------
# Streamlit page setup
# ---------------------
st.set_page_config(page_title="Money Mate", page_icon="💰")
st.title("💰 Money Mate")
st.write(
    "Your friendly AI assistant for proactive spending advice. "
    "Upload your transactions (CSV) to see forecasts and actionable tips!"
)

# ---------------------
# OpenAI API Key input
# ---------------------
api_key = st.text_input(
    "Enter your OpenAI API Key (kept private, won't be saved):",
    type="password"
)
openai.api_key = api_key

# ---------------------
# CSV Upload
# ---------------------
uploaded_file = st.file_uploader(
    "Upload your transaction CSV (columns: Date, Description, Category, Amount)",
    type="csv"
)

if uploaded_file is not None:
    try:
        # Read CSV
        df = pd.read_csv(uploaded_file)
        df.columns = df.columns.str.strip()  # remove spaces in headers

        # Ensure necessary columns
        required_cols = ["Date", "Description", "Category", "Amount"]
        if not all(col in df.columns for col in required_cols):
            st.error(f"CSV must contain columns: {', '.join(required_cols)}")
        else:
            # Convert Date
            df['Date'] = pd.to_datetime(df['Date'])

            # Show raw data
            st.write("### Raw Transactions")
            st.dataframe(df)

            # ---------------------
            # Budget Defaults (Cupertino)
            # ---------------------
            category_budgets = {
                "Food": 100,          # weekly
                "Entertainment": 60,
                "Transport": 50,
                "Subscriptions": 50,
                "Misc": 50
            }

            # ---------------------
            # Weekly Forecast
            # ---------------------
            current_week = datetime.now().isocalendar()[1]
            df['Week'] = df['Date'].dt.isocalendar().week
            weekly_df = df[df['Week'] == current_week]

            weekly_spend = weekly_df.groupby('Category')['Amount'].sum().abs().to_dict()

            # ---------------------
            # Identify Top 3 Overspending Categories
            # ---------------------
            overspending = []
            safe_categories = []
            for cat, budget in category_budgets.items():
                spent = weekly_spend.get(cat, 0)
                if spent > budget:
                    overspending.append((cat, spent, budget))
                else:
                    safe_categories.append(cat)

            overspending.sort(key=lambda x: x[1] - x[2], reverse=True)
            top_overspending = overspending[:3]  # only top 3

            # ---------------------
            # Construct AI Prompt (Strict)
            # ---------------------
            if top_overspending:
                prompt_lines = [
                    "You are Money Mate, a friendly personal finance coach.",
                    "The user is overspending in these categories:"
                ]
                for cat, spent, budget in top_overspending:
                    prompt_lines.append(f"- {cat}: ${spent:.2f} (budget: ${budget})")

                prompt_lines.append(f"""Provide 2-3 short, actionable tips (<50 words each) to help the user reduce overspending in these categories next week.
Be proactive, friendly, concise, and include emojis if useful.
⚠️ IMPORTANT: ONLY give advice for the overspending categories listed above.
Do NOT mention any safe categories: {', '.join(safe_categories)}.
Do NOT give generic advice about safe categories like Food or Subscriptions.""")
            else:
                prompt_lines = [
                    "You are Money Mate, a friendly personal finance coach.",
                    "The user is within budget for all categories.",
                    "Provide 1-2 short, positive reinforcement tips (<50 words each) to help the user maintain good spending habits. Include emojis if useful."
                ]

            prompt = "\n".join(prompt_lines)

            # ---------------------
            # Call OpenAI API
            # ---------------------
            advice = "AI quota/API issue detected. Showing mock advice:\n"
            if api_key:
                try:
                    response = openai.chat.completions.create(
                        model="gpt-3.5-turbo",
                        messages=[{"role": "user", "content": prompt}],
                        max_tokens=200,
                        temperature=0.7
                    )
                    advice = response.choices[0].message.content
                except Exception as e:
                    advice += f"(Error: {e})\nProviding a mock recommendation instead."

            # ---------------------
            # Display AI Advice
            # ---------------------
            st.write("### 💡 Money Mate Advice")
            st.info(advice)

            # ---------------------
            # Display Spending vs Budget
            # ---------------------
            st.write("### 📊 Weekly Spending vs Budget")
            summary_df = pd.DataFrame(columns=["Category", "Spent", "Budget", "Status"])
            for cat, budget in category_budgets.items():
                spent = weekly_spend.get(cat, 0)
                status = "✅ Safe" if spent <= budget else "⚠️ Over"
                summary_df = pd.concat(
                    [summary_df, pd.DataFrame([{"Category": cat, "Spent": spent, "Budget": budget, "Status": status}])],
                    ignore_index=True
                )
            st.dataframe(summary_df)

    except Exception as e:
        st.error(f"Error reading CSV: {e}")
