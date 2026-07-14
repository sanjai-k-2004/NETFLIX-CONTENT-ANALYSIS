import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st


st.set_page_config(
    page_title="Netflix Content Dashboard",
    page_icon="N",
    layout="wide",
)


MONTH_ORDER = [
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
]

DAY_ORDER = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
]


def get_season(month: int) -> str:
    if month in [12, 1, 2]:
        return "Winter"
    if month in [3, 4, 5]:
        return "Spring"
    if month in [6, 7, 8]:
        return "Summer"
    return "Autumn"


@st.cache_data
def load_data() -> pd.DataFrame:
    df = pd.read_csv("netflix_content.csv")
    df["Hours Viewed"] = (
        df["Hours Viewed"]
        .astype(str)
        .str.replace(",", "", regex=False)
        .astype(float)
    )
    df["Release Date"] = pd.to_datetime(df["Release Date"], errors="coerce")
    df = df.dropna(subset=["Release Date"]).copy()
    df["Release Year"] = df["Release Date"].dt.year
    df["Release Month"] = df["Release Date"].dt.month
    df["Release Month Name"] = pd.Categorical(
        df["Release Date"].dt.month_name(),
        categories=MONTH_ORDER,
        ordered=True,
    )
    df["Release Day"] = pd.Categorical(
        df["Release Date"].dt.day_name(),
        categories=DAY_ORDER,
        ordered=True,
    )
    df["Season"] = df["Release Month"].apply(get_season)
    return df


def indian_units(value: float) -> str:
    if value >= 1_00_00_00_000:
        return f"{value / 1_00_00_00_000:.2f}B hrs"
    if value >= 1_00_00_000:
        return f"{value / 1_00_00_000:.2f}Cr hrs"
    if value >= 1_00_000:
        return f"{value / 1_00_000:.2f}L hrs"
    return f"{value:,.0f} hrs"


def apply_filters(df: pd.DataFrame) -> pd.DataFrame:
    st.sidebar.header("User Input")

    content_types = sorted(df["Content Type"].dropna().unique().tolist())
    languages = sorted(df["Language Indicator"].dropna().unique().tolist())
    global_options = sorted(df["Available Globally?"].dropna().unique().tolist())
    years = sorted(df["Release Year"].dropna().unique().tolist())

    selected_types = st.sidebar.multiselect(
        "Content Type",
        options=content_types,
        default=content_types,
    )
    selected_languages = st.sidebar.multiselect(
        "Language",
        options=languages,
        default=languages[: min(8, len(languages))] if len(languages) > 8 else languages,
    )
    selected_global = st.sidebar.multiselect(
        "Available Globally?",
        options=global_options,
        default=global_options,
    )
    selected_years = st.sidebar.slider(
        "Release Year Range",
        min_value=int(min(years)),
        max_value=int(max(years)),
        value=(int(min(years)), int(max(years))),
    )
    title_search = st.sidebar.text_input("Search Title", "")
    top_n = st.sidebar.slider("Top Titles to Show", min_value=5, max_value=20, value=10)

    filtered = df[
        df["Content Type"].isin(selected_types)
        & df["Language Indicator"].isin(selected_languages)
        & df["Available Globally?"].isin(selected_global)
        & df["Release Year"].between(selected_years[0], selected_years[1])
    ].copy()

    if title_search.strip():
        filtered = filtered[
            filtered["Title"].str.contains(title_search.strip(), case=False, na=False)
        ]

    st.sidebar.caption(f"Filtered titles: {len(filtered):,}")
    st.session_state["top_n"] = top_n
    return filtered


def empty_state() -> None:
    st.warning("No data matches the selected filters. Adjust the user input in the sidebar.")


def slide_one(df: pd.DataFrame) -> None:
    st.subheader("Slide 1: Content Overview")

    total_hours = df["Hours Viewed"].sum()
    total_titles = df["Title"].nunique()
    avg_hours = df["Hours Viewed"].mean()
    top_language = (
        df.groupby("Language Indicator")["Hours Viewed"].sum().sort_values(ascending=False).index[0]
        if not df.empty
        else "N/A"
    )

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Hours Viewed", indian_units(total_hours))
    c2.metric("Unique Titles", f"{total_titles:,}")
    c3.metric("Average Hours per Title", indian_units(avg_hours))
    c4.metric("Top Language", top_language)

    left, right = st.columns(2)

    content_view = (
        df.groupby("Content Type", as_index=False)["Hours Viewed"].sum().sort_values("Hours Viewed", ascending=False)
    )
    fig_content = px.bar(
        content_view,
        x="Content Type",
        y="Hours Viewed",
        color="Content Type",
        title="Hours Viewed by Content Type",
        text_auto=".2s",
    )
    fig_content.update_layout(showlegend=False)
    left.plotly_chart(fig_content, use_container_width=True)

    language_view = (
        df.groupby("Language Indicator", as_index=False)["Hours Viewed"]
        .sum()
        .sort_values("Hours Viewed", ascending=False)
        .head(10)
    )
    fig_language = px.bar(
        language_view,
        x="Language Indicator",
        y="Hours Viewed",
        color="Hours Viewed",
        title="Top 10 Languages by Hours Viewed",
        text_auto=".2s",
    )
    right.plotly_chart(fig_language, use_container_width=True)


def slide_two(df: pd.DataFrame) -> None:
    st.subheader("Slide 2: Release Timing and Trends")

    left, right = st.columns(2)

    monthly = (
        df.groupby(["Release Year", "Release Month", "Release Month Name"], as_index=False)["Hours Viewed"]
        .sum()
        .sort_values(["Release Year", "Release Month"])
    )
    monthly["Timeline"] = (
        monthly["Release Month Name"].astype(str).str.slice(0, 3)
        + " "
        + monthly["Release Year"].astype(str)
    )
    fig_monthly = px.line(
        monthly,
        x="Timeline",
        y="Hours Viewed",
        markers=True,
        title="Monthly Viewership Trend",
    )
    fig_monthly.update_xaxes(tickangle=-45)
    left.plotly_chart(fig_monthly, use_container_width=True)

    seasonal = (
        df.groupby("Season", as_index=False)["Hours Viewed"].sum().sort_values("Hours Viewed", ascending=False)
    )
    fig_season = px.pie(
        seasonal,
        names="Season",
        values="Hours Viewed",
        hole=0.45,
        title="Seasonal Share of Viewership",
    )
    right.plotly_chart(fig_season, use_container_width=True)

    weekday = (
        df.groupby("Release Day", as_index=False)["Hours Viewed"].sum().sort_values("Release Day")
    )
    monthly_releases = (
        df.groupby("Release Month Name", as_index=False)
        .agg(Titles=("Title", "count"), Hours_Viewed=("Hours Viewed", "sum"))
        .sort_values("Release Month Name")
    )

    bottom_left, bottom_right = st.columns(2)
    fig_weekday = px.bar(
        weekday,
        x="Release Day",
        y="Hours Viewed",
        color="Hours Viewed",
        title="Viewership by Release Day",
        category_orders={"Release Day": DAY_ORDER},
    )
    bottom_left.plotly_chart(fig_weekday, use_container_width=True)

    fig_combo = go.Figure()
    fig_combo.add_bar(
        x=monthly_releases["Release Month Name"],
        y=monthly_releases["Titles"],
        name="Titles Released",
        marker_color="#E50914",
    )
    fig_combo.add_scatter(
        x=monthly_releases["Release Month Name"],
        y=monthly_releases["Hours_Viewed"],
        name="Hours Viewed",
        mode="lines+markers",
        yaxis="y2",
        line=dict(color="#221F1F", width=3),
    )
    fig_combo.update_layout(
        title="Monthly Releases vs Viewership",
        xaxis=dict(categoryorder="array", categoryarray=MONTH_ORDER),
        yaxis=dict(title="Titles Released"),
        yaxis2=dict(title="Hours Viewed", overlaying="y", side="right"),
        legend=dict(orientation="h", y=1.08),
    )
    bottom_right.plotly_chart(fig_combo, use_container_width=True)


def slide_three(df: pd.DataFrame, top_n: int) -> None:
    st.subheader("Slide 3: Top Titles")

    top_titles = df.nlargest(top_n, "Hours Viewed")[
        [
            "Title",
            "Hours Viewed",
            "Language Indicator",
            "Content Type",
            "Available Globally?",
            "Release Date",
        ]
    ].copy()
    top_titles["Release Date"] = top_titles["Release Date"].dt.strftime("%Y-%m-%d")

    fig_top_titles = px.bar(
        top_titles.sort_values("Hours Viewed"),
        x="Hours Viewed",
        y="Title",
        orientation="h",
        color="Content Type",
        hover_data=["Language Indicator", "Available Globally?", "Release Date"],
        title=f"Top {top_n} Titles by Hours Viewed",
    )
    st.plotly_chart(fig_top_titles, use_container_width=True)

    col1, col2 = st.columns([1.1, 0.9])

    scatter = px.scatter(
        df,
        x="Release Year",
        y="Hours Viewed",
        color="Content Type",
        size="Hours Viewed",
        hover_name="Title",
        hover_data=["Language Indicator", "Available Globally?"],
        title="Title Performance by Release Year",
    )
    col1.plotly_chart(scatter, use_container_width=True)

    summary = (
        df.groupby(["Language Indicator", "Content Type"], as_index=False)
        .agg(
            Titles=("Title", "count"),
            Total_Hours=("Hours Viewed", "sum"),
            Avg_Hours=("Hours Viewed", "mean"),
        )
        .sort_values("Total_Hours", ascending=False)
        .head(15)
    )
    col2.dataframe(summary, use_container_width=True, hide_index=True)

    csv = top_titles.to_csv(index=False).encode("utf-8")
    st.download_button(
        "Download filtered top titles",
        data=csv,
        file_name="filtered_top_titles.csv",
        mime="text/csv",
    )


def slide_four(df: pd.DataFrame) -> None:
    st.subheader("Slide 4: Strategy Insights")

    col1, col2, col3 = st.columns(3)

    best_type = (
        df.groupby("Content Type")["Hours Viewed"].sum().sort_values(ascending=False).index[0]
    )
    best_language = (
        df.groupby("Language Indicator")["Hours Viewed"].sum().sort_values(ascending=False).index[0]
    )
    best_season = (
        df.groupby("Season")["Hours Viewed"].sum().sort_values(ascending=False).index[0]
    )

    col1.metric("Highest Performing Format", best_type)
    col2.metric("Highest Performing Language", best_language)
    col3.metric("Strongest Season", best_season)

    left, right = st.columns([1.05, 0.95])

    strategy_table = (
        df.groupby(["Content Type", "Language Indicator"], as_index=False)
        .agg(
            Titles=("Title", "count"),
            Total_Hours=("Hours Viewed", "sum"),
            Avg_Hours=("Hours Viewed", "mean"),
        )
        .sort_values(["Total_Hours", "Avg_Hours"], ascending=False)
        .head(12)
    )
    left.dataframe(strategy_table, use_container_width=True, hide_index=True)

    yearly_type = (
        df.groupby(["Release Year", "Content Type"], as_index=False)["Hours Viewed"].sum()
    )
    fig_yearly_type = px.area(
        yearly_type,
        x="Release Year",
        y="Hours Viewed",
        color="Content Type",
        title="Yearly Viewership Mix by Content Type",
    )
    right.plotly_chart(fig_yearly_type, use_container_width=True)

    insights = [
        f"Focus on {best_type.lower()} content because it leads total filtered viewership.",
        f"Prioritize {best_language} titles since that language contributes the most hours viewed.",
        f"Plan major releases in {best_season.lower()} when audience response is strongest in this selection.",
    ]
    st.markdown("### Strategic Recommendations")
    for item in insights:
        st.write(f"- {item}")


def main() -> None:
    st.title("Netflix Content Strategy Analysis")
    st.caption("Interactive 4-slide dashboard built from your notebook analysis with live user input filters.")

    df = load_data()
    filtered = apply_filters(df)

    if filtered.empty:
        empty_state()
        return

    slide1, slide2, slide3, slide4 = st.tabs(
        [
            "Slide 1 - Overview",
            "Slide 2 - Trends",
            "Slide 3 - Top Titles",
            "Slide 4 - Strategy",
        ]
    )

    with slide1:
        slide_one(filtered)

    with slide2:
        slide_two(filtered)

    with slide3:
        slide_three(filtered, st.session_state["top_n"])

    with slide4:
        slide_four(filtered)


if __name__ == "__main__":
    main()
