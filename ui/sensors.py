import pandas as pd
import streamlit as st


def render_sensors_page(twin_system):
    bin_data = twin_system.get_all_bins()
    bin_ids = list(bin_data)
    average_fill = round(sum(item["fill_level"] for item in bin_data.values()) / max(1, len(bin_data)))
    total_volume = sum(item["fill_volume_liters"] for item in bin_data.values())
    critical_count = sum(item["status"] == "Critical" for item in bin_data.values())

    st.markdown('<div class="page-heading">Sensor Network</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="page-subtitle">Ultrasonic level, temperature and battery telemetry for each smart bin</div>',
        unsafe_allow_html=True,
    )

    metric_columns = st.columns(3)
    metric_columns[0].metric("Average fill", f"{average_fill}%")
    metric_columns[1].metric("Estimated waste volume", f"{total_volume:,.1f} L")
    metric_columns[2].metric("Critical bins", critical_count)

    with st.container(border=True, key="sensor_readings_panel"):
        st.markdown('<div class="event-heading">Latest Sensor Readings</div>', unsafe_allow_html=True)
        st.caption("Ultrasonic distance is measured from the sensor mounted at the lid to the waste surface.")
        sensor_rows = [
            {
                "BIN": bin_id.split(" (")[0],
                "SOURCE": item["sensor_source"],
                "AIR GAP (cm)": item["ultrasonic_distance_cm"],
                "FILL HEIGHT (cm)": item["fill_height_cm"],
                "VOLUME (L)": item["fill_volume_liters"],
                "CAPACITY (L)": item["capacity_liters"],
                "FILL (%)": item["fill_level"],
                "TEMP (°C)": item["temperature"],
                "BATTERY (%)": round(item["battery"], 1),
                "STATUS": item["status"],
            }
            for bin_id, item in bin_data.items()
        ]
        st.dataframe(pd.DataFrame(sensor_rows), hide_index=True, width="stretch")

    with st.container(border=True, key="sensor_manual_reading_panel"):
        st.markdown('<div class="event-heading">Apply Ultrasonic Reading</div>', unsafe_allow_html=True)
        st.caption("Use this input to test the sensor-to-volume calculation. Live hardware is not connected yet.")
        with st.form("ultrasonic_reading_form"):
            selected_bin = st.selectbox("Bin", bin_ids)
            current_bin = bin_data[selected_bin]
            air_gap_cm = st.number_input(
                "Sensor-to-waste distance (cm)",
                min_value=0.0,
                max_value=400.0,
                value=float(current_bin["ultrasonic_distance_cm"]),
                step=0.5,
            )
            apply_reading = st.form_submit_button("Apply reading", type="primary")
        if apply_reading:
            twin_system.update_bin_from_ultrasonic(selected_bin, air_gap_cm, source="Manual entry")
            st.success(f"Updated {selected_bin.split(' (')[0]}: {twin_system.bins[selected_bin]['fill_volume_liters']:.1f} L, {twin_system.bins[selected_bin]['fill_level']:.1f}% full.")

    st.markdown(
        "**Volume model:** fill height = bin height − measured air gap. For these rectangular demo bins, liters = fill height × inner length × inner width ÷ 1,000. Irregular waste surfaces and packing density can affect accuracy.",
    )