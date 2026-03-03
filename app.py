"""
Frazer School Chess Leaderboard
--------------------------------

Features:
- Automatic medal emojis for top 3
- Collapsible scoring explanation
- Example scoring table
- FAQ section
- Top 10 scoring system
"""

import streamlit as st
import requests
import pandas as pd
from collections import defaultdict
from datetime import datetime

st.set_page_config(page_title="Frazer Chess Leaderboard", layout="wide")

st.title("🏆 Frazer School Chess Leaderboard")

TEAM_ID = "frazer-school-chess-team"
headers = {"Accept": "application/x-ndjson"}

# -----------------------------------
# Date Selection
# -----------------------------------
col1, col2 = st.columns(2)
with col1:
    start_date = st.date_input("Start Date")
with col2:
    end_date = st.date_input("End Date")


# -----------------------------------
# Fetch Team Tournaments
# -----------------------------------
@st.cache_data(show_spinner=False)
def fetch_team_tournaments():
    tournaments = []

    # Arena tournaments
    arena_url = f"https://lichess.org/api/team/{TEAM_ID}/arena"
    r = requests.get(arena_url, headers=headers, stream=True)
    if r.status_code == 200:
        for line in r.iter_lines():
            if line:
                data = pd.read_json(line.decode("utf-8"), typ="series")
                tournaments.append({
                    "id": data["id"],
                    "date": datetime.utcfromtimestamp(
                        data["startsAt"] / 1000
                    ).date(),
                    "type": "arena"
                })

    # Swiss tournaments
    swiss_url = f"https://lichess.org/api/team/{TEAM_ID}/swiss"
    r = requests.get(swiss_url, headers=headers, stream=True)
    if r.status_code == 200:
        for line in r.iter_lines():
            if line:
                data = pd.read_json(line.decode("utf-8"), typ="series")
                tournaments.append({
                    "id": data["id"],
                    "date": datetime.fromisoformat(
                        data["startsAt"].replace("Z", "+00:00")
                    ).date(),
                    "type": "swiss"
                })

    return tournaments


# -----------------------------------
# Fetch Results
# -----------------------------------
@st.cache_data(show_spinner=False)
def fetch_results(tournament_id, tournament_type):

    if tournament_type == "arena":
        url = f"https://lichess.org/api/tournament/{tournament_id}/results"
    else:
        url = f"https://lichess.org/api/swiss/{tournament_id}/results"

    r = requests.get(url, headers=headers, stream=True)
    results = []

    if r.status_code == 200:
        for line in r.iter_lines():
            if line:
                data = pd.read_json(line.decode("utf-8"), typ="series")
                results.append(data)

    return results


# -----------------------------------
# Main Logic
# -----------------------------------
if start_date and end_date:

    if start_date > end_date:
        st.error("Start date must be before end date.")
        st.stop()

    with st.spinner("Fetching tournament data..."):
        tournaments = fetch_team_tournaments()

        filtered = [
            t for t in tournaments
            if start_date <= t["date"] <= end_date
        ]

        if not filtered:
            st.warning("No tournaments found in selected date range.")
            st.stop()

        user_scores = defaultdict(list)

        for t in filtered:
            results = fetch_results(t["id"], t["type"])
            total_players = len(results)

            for player in results:
                username = player["username"]
                rank = player["rank"]
                score = total_players - rank + 1
                user_scores[username].append(score)

        leaderboard_data = []

        for user, scores in user_scores.items():
            sorted_scores = sorted(scores, reverse=True)
            top10 = sorted_scores[:10]

            leaderboard_data.append({
                "Username": user,
                "GamesPlayed": len(scores),
                "Top10TotalScore": sum(top10)
            })

        df = pd.DataFrame(leaderboard_data)
        df = df.sort_values("Top10TotalScore", ascending=False)
        df = df.reset_index(drop=True)

        # Add Rank column
        df.insert(0, "Rank", df.index + 1)

        # Add medal emojis
        def add_medal(rank):
            if rank == 1:
                return "🥇"
            elif rank == 2:
                return "🥈"
            elif rank == 3:
                return "🥉"
            else:
                return ""

        df["Medal"] = df["Rank"].apply(add_medal)

        # Move Medal next to Rank
        df = df[["Rank", "Medal", "Username", "GamesPlayed", "Top10TotalScore"]]

    # -----------------------------------
    # Collapsible Explanation Section
    # -----------------------------------
    with st.expander("📊 How Top 10 Score Is Calculated"):

        st.markdown("""
        **Scoring Formula**

        ```
        Score = Total Players − Rank + 1
        ```

        Larger tournaments give more possible points.
        """)

        st.markdown("### Example (12 Player Tournament)")

        example_df = pd.DataFrame({
            "Rank": [1, 2, 3, 12],
            "Score": [12, 11, 10, 1]
        })

        st.table(example_df)

        st.markdown("""
        **Top 10 Rule**
        - Each player's 10 highest scoring tournaments are counted.
        - If a player plays fewer than 10 tournaments,
          all tournaments are counted.
        - Leaderboard is ranked by highest Top 10 total score.
        """)

    # -----------------------------------
    # Leaderboard Display
    # -----------------------------------
    st.subheader("🏅 Leaderboard")
    st.dataframe(df, hide_index=True)

    st.download_button(
        "Download Leaderboard CSV",
        df.to_csv(index=False),
        "frazer_leaderboard.csv"
    )

    # -----------------------------------
    # FAQ Section
    # -----------------------------------
    st.markdown("---")
    st.markdown("### ❓ FAQ")

    st.markdown("""
    **Q1: Why does winning a bigger tournament give more points?**  
    Larger tournaments are more competitive, so first place is rewarded more.

    **Q2: What if a player misses tournaments?**  
    Only tournaments they played are counted.

    **Q3: Why Top 10 only?**  
    This rewards consistency and avoids penalizing students who cannot attend every week.

    **Q4: Can rankings change later?**  
    Yes. Rankings update automatically when new tournaments are included in the selected date range.
    """)