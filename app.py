import streamlit as st
from datetime import date, timedelta
from typing import Dict, Tuple
import pandas as pd

st.set_page_config(page_title="Date Span Hours Counter (Alt Weeks)", page_icon="⏱️")
st.title("⏱️ Date Span Hours Counter")

# ---------------- Inputs: Date range ----------------

st.subheader("Date Inputs")

col1, col2 = st.columns(2)
with col1:
    start_date = st.date_input("From date", value=date.today().replace(day=1))
with col2:
    end_date = st.date_input("To date", value=date.today())

if start_date > end_date:
    st.error("❗ 'From date' must be on or before 'To date'.")
    st.stop()

weekday_labels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

# ---------------- Pattern Settings ----------------
st.divider()
st.subheader("Pattern Settings")

# New: PCA vs CDPAS toggle (checkbox = CDPAS on)
cdpas_mode = st.checkbox(
    "CDPAS mode (weekly hours only)",
    value=False,
    help=(
        "When enabled, CDPAS ignores weekday selection, alternating weeks, and unit conversion. "
        "Enter a single 'Hours per week' and totals are prorated by the number of weeks in the date span."
    ),
)

# Only show alternating-weeks toggle when using PCA
use_alt_weeks = False
if not cdpas_mode:
    use_alt_weeks = st.checkbox(
        "Enable alternating weeks (Week A / Week B)",
        value=False,
        help=(
            "If enabled, the week containing the From date is Week A, and the next week is Week B, "
            "alternating thereafter (Mon–Sun weeks)."
        ),
    )

# ---------------- Helper: inclusive daterange generator ----------------
def daterange_inclusive(start: date, end: date):
    d = start
    while d <= end:
        yield d
        d += timedelta(days=1)

# ---------------- Helpers: unit conversion ----------------
def convert_total(base_hours: float, day_count: int, unit: str) -> float:
    if unit == "Hourly":
        return base_hours
    elif unit == "15 mins":
        return base_hours * 4
    elif unit == "Per diem":
        return float(day_count)  # ignore hours, count days
    return base_hours

# ---------------- Single-pattern UI (no alternation) ----------------
def single_pattern_ui() -> Tuple[Dict[int, int], Dict[int, float]]:
    st.markdown("**Include which weekdays?** (check any)")
    checks = []
    for i, col in enumerate(st.columns(7)):
        with col:
            checks.append(st.checkbox(weekday_labels[i], value=(i < 5)))
    selected_weekdays = {i for i, v in enumerate(checks) if v}
    if not selected_weekdays:
        st.info("Select at least one weekday.")
        st.stop()

    st.subheader("Hours per Day (Single Pattern)")
    same_hours = st.checkbox("Use the same hours per day for all selected weekdays", value=True)
    weekday_hours: Dict[int, float] = {}
    if same_hours:
        hrs = st.number_input(
            "Hours per day (applies to all selected weekdays)",
            min_value=0.0, max_value=24.0, step=0.25, value=8.0
        )
        for wd in selected_weekdays:
            weekday_hours[wd] = hrs
    else:
        st.caption("Set hours per day for each selected weekday:")
        for i, col in enumerate(st.columns(7)):
            if i in selected_weekdays:
                with col:
                    default = 8.0 if i < 5 else 0.0
                    weekday_hours[i] = st.number_input(
                        f"{weekday_labels[i]} hrs",
                        min_value=0.0, max_value=24.0, step=0.25, value=default,
                        key=f"hrs_{i}"
                    )

    # Count occurrences per weekday (single pattern math)
    def count_total_days(start: date, end: date) -> int:
        return (end - start).days + 1

    def count_weekday(start: date, end: date, target_wd: int) -> int:
        total_days = count_total_days(start, end)
        full_weeks = total_days // 7
        count = full_weeks  # one of each weekday per full week
        remainder = total_days % 7
        start_wd = start.weekday()
        for i in range(remainder):
            if (start_wd + i) % 7 == target_wd:
                count += 1
        return count

    selected_counts = {wd: count_weekday(start_date, end_date, wd) for wd in selected_weekdays}
    return selected_counts, weekday_hours

# ---------------- Alternating-pattern UI ----------------
def alternating_pattern_ui() -> Tuple[Dict[str, Dict[int, int]], Dict[str, Dict[int, float]]]:
    # Week A selection
    st.markdown("**Week A: select weekdays**")
    checks_A = []
    for i, col in enumerate(st.columns(7)):
        with col:
            checks_A.append(st.checkbox(f"A-{weekday_labels[i]}", value=(i < 5), key=f"A_chk_{i}"))
    wds_A = {i for i, v in enumerate(checks_A) if v}

    st.caption("Week A hours per day")
    same_A = st.checkbox("Use the same hours per day for all Week A selected weekdays", value=True, key="A_same")
    hrs_A: Dict[int, float] = {}
    if same_A:
        h = st.number_input("Week A hours per day", min_value=0.0, max_value=24.0, step=0.25, value=8.0, key="A_all")
        for wd in wds_A:
            hrs_A[wd] = h
    else:
        for i, col in enumerate(st.columns(7)):
            if i in wds_A:
                with col:
                    default = 8.0 if i < 5 else 0.0
                    hrs_A[i] = st.number_input(
                        f"A {weekday_labels[i]} hrs", min_value=0.0, max_value=24.0, step=0.25,
                        value=default, key=f"A_hrs_{i}"
                    )

    st.markdown("---")
    # Week B selection
    st.markdown("**Week B: select weekdays**")
    checks_B = []
    for i, col in enumerate(st.columns(7)):
        with col:
            # Default Week B to same Mon–Fri initially
            checks_B.append(st.checkbox(f"B-{weekday_labels[i]}", value=(i < 5), key=f"B_chk_{i}"))
    wds_B = {i for i, v in enumerate(checks_B) if v}

    st.caption("Week B hours per day")
    same_B = st.checkbox("Use the same hours per day for all Week B selected weekdays", value=True, key="B_same")
    hrs_B: Dict[int, float] = {}
    if same_B:
        h = st.number_input("Week B hours per day", min_value=0.0, max_value=24.0, step=0.25, value=8.0, key="B_all")
        for wd in wds_B:
            hrs_B[wd] = h
    else:
        for i, col in enumerate(st.columns(7)):
            if i in wds_B:
                with col:
                    default = 8.0 if i < 5 else 0.0
                    hrs_B[i] = st.number_input(
                        f"B {weekday_labels[i]} hrs", min_value=0.0, max_value=24.0, step=0.25,
                        value=default, key=f"B_hrs_{i}"
                    )

    if not wds_A and not wds_B:
        st.info("Select at least one weekday in Week A or Week B.")
        st.stop()

    # Count occurrences by iterating days and assigning A/B by week parity
    # Definition: Week A is the ISO week starting Monday that contains the From date.
    # We compute week_index from the Monday of the From date: parity 0 = A, 1 = B.
    def monday_of_week(d: date) -> date:
        return d - timedelta(days=d.weekday())  # Monday

    anchor_monday = monday_of_week(start_date)

    counts = {"A": {i: 0 for i in range(7)}, "B": {i: 0 for i in range(7)}}
    for d in daterange_inclusive(start_date, end_date):
        week_index = ((d - anchor_monday).days // 7) % 2
        bucket = "A" if week_index == 0 else "B"
        counts[bucket][d.weekday()] += 1

    hours = {"A": {i: 0.0 for i in range(7)}, "B": {i: 0.0 for i in range(7)}}
    for i in range(7):
        hours["A"][i] = hrs_A.get(i, 0.0)
        hours["B"][i] = hrs_B.get(i, 0.0)

    # Zero out days not selected in each pattern
    for i in range(7):
        if i not in wds_A:
            counts["A"][i] = 0
            hours["A"][i] = 0.0
        if i not in wds_B:
            counts["B"][i] = 0
            hours["B"][i] = 0.0

    return counts, hours

# ---------------- PCA: Unit Conversion (hidden in CDPAS) ----------------
if not cdpas_mode:
    st.subheader("Unit Conversion")
    unit_option = st.selectbox(
        "Select unit conversion:",
        ["Hourly", "15 mins", "Per diem"],
        help="Hourly: hours stay the same. 15 mins: hours × 4. Per diem: ignore hours and count days."
    )

# ---------------- Compute & Display ----------------
if cdpas_mode:
    # --- CDPAS branch ---
    st.subheader("CDPAS Settings")
    hours_per_week = st.number_input(
        "Hours per week",
        min_value=0.0,
        max_value=168.0,
        step=0.25,
        value=40.0,
        help="Enter the approved weekly hours. Totals are prorated by (calendar days ÷ 7).",
    )

    total_calendar_days = (end_date - start_date).days + 1
    weeks_in_span = total_calendar_days / 7.0  # prorated weeks

    total_hours = hours_per_week * weeks_in_span
    total_15min_units = total_hours * 4

    st.divider()
    st.subheader("Results (CDPAS)")

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Total calendar days (inclusive)", total_calendar_days)
    with c2:
        st.metric("Weeks in range (prorated)", f"{weeks_in_span:,.2f}")
    with c3:
        st.metric("Total hours", f"{total_hours:,.2f}")
    with c4:
        st.metric("Total 15-min units", f"{total_15min_units:,.2f}")

    with st.expander("Calculation details"):
        st.write(
            """
            **Formula**: `Total hours = Hours per week × (calendar days ÷ 7)`.
            The date span is inclusive of both From and To dates. 15-minute units are hours × 4.
            """
        )

else:
    # --- PCA branch (existing calculator) ---
    if not use_alt_weeks:
        selected_counts, weekday_hours = single_pattern_ui()

        total_calendar_days = (end_date - start_date).days + 1
        total_matching_days = sum(selected_counts.values())
        base_hours = sum(selected_counts[wd] * weekday_hours.get(wd, 0.0) for wd in selected_counts)

        final_total = convert_total(base_hours, total_matching_days, unit_option)

        st.divider()
        st.subheader("Results (Single Pattern)")
        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("Total calendar days (inclusive)", total_calendar_days)
        with c2:
            st.metric("Days matching selection", total_matching_days)
        with c3:
            label = {"Hourly": "Total hours", "15 mins": "Total 15-min units", "Per diem": "Total per-diems (days)"}[unit_option]
            st.metric(label, f"{final_total:,.2f}")

        with st.expander("Breakdown by weekday"):
            rows = []
            for wd in sorted(selected_counts.keys()):
                day_count = selected_counts[wd]
                base = day_count * weekday_hours.get(wd, 0.0)
                converted = convert_total(base, day_count, unit_option)
                rows.append({
                    "Weekday": weekday_labels[wd],
                    "Count in range": day_count,
                    "Hours per day": weekday_hours.get(wd, 0.0),
                    "Converted total": converted
                })
            st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)

    else:
        counts_AB, hours_AB = alternating_pattern_ui()

        total_calendar_days = (end_date - start_date).days + 1
        # Summaries
        total_days_A = sum(counts_AB["A"].values())
        total_days_B = sum(counts_AB["B"].values())
        total_matching_days = total_days_A + total_days_B

        base_hours_A = sum(counts_AB["A"][wd] * hours_AB["A"].get(wd, 0.0) for wd in range(7))
        base_hours_B = sum(counts_AB["B"][wd] * hours_AB["B"].get(wd, 0.0) for wd in range(7))
        base_hours_total = base_hours_A + base_hours_B

        final_total_A = convert_total(base_hours_A, total_days_A, unit_option)
        final_total_B = convert_total(base_hours_B, total_days_B, unit_option)
        final_total = final_total_A + final_total_B

        st.divider()
        st.subheader("Results (Alternating Weeks)")

        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.metric("Total calendar days (inclusive)", total_calendar_days)
        with c2:
            st.metric("Days in Week A pattern", total_days_A)
        with c3:
            st.metric("Days in Week B pattern", total_days_B)
        with c4:
            label = {"Hourly": "Total hours", "15 mins": "Total 15-min units", "Per diem": "Total per-diems (days)"}[unit_option]
            st.metric(label, f"{final_total:,.2f}")

        with st.expander("Breakdown by pattern and weekday"):
            rows = []
            for bucket in ["A", "B"]:
                for wd in range(7):
                    day_count = counts_AB[bucket][wd]
                    base = day_count * hours_AB[bucket].get(wd, 0.0)
                    converted = convert_total(base, day_count, unit_option)
                    rows.append({
                        "Pattern": f"Week {bucket}",
                        "Weekday": weekday_labels[wd],
                        "Count in range": day_count,
                        "Hours per day": hours_AB[bucket].get(wd, 0.0),
                        "Converted total": converted
                    })
            df = pd.DataFrame(rows)
            # Keep only non-zero rows for a cleaner table
            df = df[(df["Count in range"] > 0) | (df["Converted total"] > 0)]
            st.dataframe(df, hide_index=True, use_container_width=True)
