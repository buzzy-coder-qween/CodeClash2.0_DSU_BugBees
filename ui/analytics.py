import pandas as pd
import streamlit as st


def render_analytics_page(twin_system):
    bin_data = twin_system.get_all_bins()
    current_rows = [
        {
            "BIN": bin_id.split(" (")[0],
            "WASTE TYPE": item["type"],
            "FILL (%)": item["fill_level"],
            "VOLUME (L)": item["fill_volume_liters"],
            "CAPACITY (L)": item["capacity_liters"],
            "STATUS": item["status"],
        }
        for bin_id, item in bin_data.items()
    ]
    current_df = pd.DataFrame(current_rows)
    total_volume = current_df["VOLUME (L)"].sum()
    total_capacity = current_df["CAPACITY (L)"].sum()
    overall_fill = total_volume / total_capacity * 100 if total_capacity else 0
    history_df = pd.DataFrame(twin_system.get_history())

    st.markdown('<div class="page-heading">Waste Analytics</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="page-subtitle">Volume-based capacity, ultrasonic fill trends and bin utilization</div>',
        unsafe_allow_html=True,
    )

    metric_columns = st.columns(3)
    metric_columns[0].metric("Waste volume", f"{total_volume:,.1f} L")
    metric_columns[1].metric("Combined capacity", f"{total_capacity:,.1f} L")
    metric_columns[2].metric("Capacity used", f"{overall_fill:.1f}%")

    chart_column, volume_column = st.columns(2, gap="medium")
    with chart_column, st.container(border=True, key="analytics_fill_trend"):
        st.markdown('<div class="event-heading">Fill Level Trend</div>', unsafe_allow_html=True)
        st.caption("Derived from ultrasonic air-gap measurements; use Simulate sensor update to add a sample.")
        if not history_df.empty:
            history_df["recorded_at"] = pd.to_datetime(history_df["recorded_at"])
            if history_df["recorded_at"].nunique() >= 2:
                st.line_chart(
                    history_df,
                    x="recorded_at",
                    y="fill_percent",
                    color="bin_id",
                    x_label="Reading time",
                    y_label="Fill (%)",
                    height=260,
                )
            else:
                st.info("A trend appears after a second sensor reading. Apply a manual reading or simulate an update.")
        else:
            st.info("No sensor history recorded yet.")

    with volume_column, st.container(border=True, key="analytics_volume_by_bin"):
        st.markdown('<div class="event-heading">Current Volume by Bin</div>', unsafe_allow_html=True)
        st.caption("Estimated waste volume compared with each bin’s measured capacity.")
        st.bar_chart(current_df, x="BIN", y="VOLUME (L)", color="#46d8ad", height=260)

    with st.container(border=True, key="analytics_capacity_table"):
        st.markdown('<div class="event-heading">Capacity Summary</div>', unsafe_allow_html=True)
        st.dataframe(current_df, hide_index=True, width="stretch")