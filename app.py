import streamlit as st
import requests
import pandas as pd
import json
from collections import defaultdict
from datetime import datetime, date
import calendar
from pathlib import Path

# -------------------------------------------------------
# PAGE CONFIG
# -------------------------------------------------------
st.set_page_config(
    page_title="Frazer Chess Leaderboard",
    layout="wide"
)

# -------------------------------------------------------
# HEADER WITH FALCON LOGO
# -------------------------------------------------------
col1, col2 = st.columns([1, 5])

with col1:
    logo_path = Path(__file__).parent / "assets" / "falcon.png"
    if logo_path.exists():
        st.image(str(logo_path), width=120)

with col2:
    st.markdown(
        "<h1 style='margin-top:30px;'>🏆 Frazer School Chess Leaderboard</h1>",
        unsafe_allow_html=True
    )

TEAM_ID = "frazer-school-chess-team"
headers = {"Accept": "application/x-ndjson"}

# -------------------------------------------------------
# FLEXIBLE DATE SELECTION
# -------------------------------------------------------
today = date.today()

col1, col2 = st.columns(2)
with col1:
    start_date = st.date_input("Start Date", value=date(today.year, today.month, 1))
with col2:
    end_date = st.date_input("End Date", value=today)

if start_date > end_date:
    st.error("Start date must be before end date.")
    st.stop()

# -------------------------------------------------------
# FETCH TOURNAMENTS
# -------------------------------------------------------
@st.cache_data(ttl=3600, show_spinner=False)
def fetch_team_tournaments():
    tournaments = []

    # Arena tournaments
    arena_url = f"https://lichess.org/api/team/{TEAM_ID}/arena"
    r = requests.get(arena_url, headers=headers, stream=True, timeout=30)
    if r.status_code == 200:
        for line in r.iter_lines():
            if line:
                data = json.loads(line.decode("utf-8"))
                tournaments.append({
                    "id": data["id"],
                    "date": datetime.utcfromtimestamp(
                        data["startsAt"] / 1000
                    ).date(),
                    "type": "arena",
                    "name": data.get("fullName", data.get("name", "")).lower()
                })

    # Swiss tournaments
    swiss_url = f"https://lichess.org/api/team/{TEAM_ID}/swiss"
    r = requests.get(swiss_url, headers=headers, stream=True, timeout=30)
    if r.status_code == 200:
        for line in r.iter_lines():
            if line:
                data = json.loads(line.decode("utf-8"))
                tournaments.append({
                    "id": data["id"],
                    "date": datetime.fromisoformat(
                        data["startsAt"].replace("Z", "+00:00")
                    ).date(),
                    "type": "swiss",
                    "name": data.get("name", "").lower()
                })

    return tournaments


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_results(tid, ttype):
    if ttype == "arena":
        url = f"https://lichess.org/api/tournament/{tid}/results"
    else:
        url = f"https://lichess.org/api/swiss/{tid}/results"

    r = requests.get(url, headers=headers, stream=True, timeout=30)
    results = []

    if r.status_code == 200:
        for line in r.iter_lines():
            if line:
                results.append(json.loads(line.decode("utf-8")))

    return results


def build_dataframe(score_dict):
    leaderboard_data = []

    for user, scores in score_dict.items():
        sorted_scores = sorted(scores, reverse=True)
        top10 = sorted_scores[:10]

        leaderboard_data.append({
            "Username": user,
            "GamesPlayed": len(scores),
            "Top10TotalScore": sum(top10)
        })

    if not leaderboard_data:
        return pd.DataFrame(columns=["Rank", "Medal", "Username", "GamesPlayed", "Top10TotalScore"])

    df = pd.DataFrame(leaderboard_data)
    df = df.sort_values("Top10TotalScore", ascending=False).reset_index(drop=True)
    df.insert(0, "Rank", df.index + 1)

    df["Medal"] = df["Rank"].apply(
        lambda r: "🥇" if r == 1 else
                  "🥈" if r == 2 else
                  "🥉" if r == 3 else ""
    )

    return df[["Rank", "Medal", "Username", "GamesPlayed", "Top10TotalScore"]]


# -------------------------------------------------------
# BUILD LEADERBOARD
# -------------------------------------------------------
with st.spinner("Fetching data..."):
    tournaments = fetch_team_tournaments()

    filtered = [
        t for t in tournaments
        if start_date <= t["date"] <= end_date
    ]

    if not filtered:
        st.warning("No tournaments found in this date range.")
        st.stop()

    overall_scores = defaultdict(list)

    for t in filtered:
        results = fetch_results(t["id"], t["type"])
        total_players = len(results)

        for player in results:
            username = player["username"]
            rank = player["rank"]
            score = total_players - rank + 1
            overall_scores[username].append(score)

    df = build_dataframe(overall_scores)

# -------------------------------------------------------
# SCORING EXPLANATION
# -------------------------------------------------------
with st.expander("📊 How Scoring Works"):
    st.markdown("""
Score = Total Players − Rank + 1

Example with 12 players:
- 1st place = 12 points
- 2nd place = 11 points
- 3rd place = 10 points
- 12th place = 1 point

For each player, we count their 10 highest scoring tournaments in the selected date range.
If they played fewer than 10 tournaments, all of their tournaments are counted.
""")

    example_df = pd.DataFrame({
        "Rank": [1, 2, 3, 12],
        "Score": [12, 11, 10, 1]
    })
    st.table(example_df)

# -------------------------------------------------------
# LEADERBOARD DISPLAY
# -------------------------------------------------------
st.subheader("🏅 Leaderboard")
st.dataframe(df, hide_index=True)

st.download_button(
    label="Download Leaderboard as CSV",
    data=df.to_csv(index=False),
    file_name="frazer_leaderboard.csv",
    mime="text/csv"
)

# -------------------------------------------------------
# FAQ
# -------------------------------------------------------
st.markdown("---")
st.markdown("### ❓ FAQ")
st.markdown("""
Why do larger tournaments give more points?  
Because beating more players is more competitive.

What if a student misses tournaments?  
Only tournaments they played are counted.

Does the leaderboard update automatically?  
Yes. It pulls data directly from Lichess.
""")