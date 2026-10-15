from datetime import datetime

import pandas as pd
import streamlit as st


def render_bin_network_page(twin_system):
    bins = twin_system.get_all_bins()
    bin_ids = list(bins)
    average_fill = sum(item["fill_level"] for item in bins.values()) / max(1, len(bins))
    critical_count = sum(item["status"] == "Critical" for item in bins.values())
    total_volume = sum(item["fill_volume_liters"] for item in bins.values())

    st.markdown('<div class="page-heading">Bin Network</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="page-subtitle">Inspect, filter, and service bins across the digital twin</div>',
        unsafe_allow_html=True,
    )

    metric_columns = st.columns(4)
    metric_columns[0].metric("Connected bins", len(bins))
    metric_columns[1].metric("Average fill", f"{average_fill:.1f}%")
    metric_columns[2].metric("Critical", critical_count)
    metric_columns[3].metric("Estimated volume", f"{total_volume:.1f} L")

    search_column, status_column, type_column = st.columns([1.5, 1, 1])
    search = search_column.text_input("Search bin", placeholder="Bin ID or location", key="bin_network_search")
    status_filter = status_column.selectbox("Status", ["All", "Critical", "Warning", "Normal"], key="bin_network_status")
    waste_types = sorted({item["type"] for item in bins.values()})
    type_filter = type_column.selectbox("Waste type", ["All", *waste_types], key="bin_network_type")

    visible_bins = {
        bin_id: item for bin_id, item in bins.items()
        if (not search or search.casefold() in bin_id.casefold())
        and (status_filter == "All" or item["status"] == status_filter)
        and (type_filter == "All" or item["type"] == type_filter)
    }
    rows = [
        {
            "BIN": bin_id,
            "WASTE TYPE": item["type"],
            "STATUS": item["status"],
            "FILL (%)": item["fill_level"],
            "VOLUME (L)": item["fill_volume_liters"],
            "ULTRASONIC AIR GAP (cm)": item["ultrasonic_distance_cm"],
            "TEMP (°C)": item["temperature"],
            "BATTERY (%)": round(item["battery"], 1),
            "LAST EMPTIED": item["emptied_at"],
        }
        for bin_id, item in visible_bins.items()
    ]

    with st.container(border=True, key="bin_network_table_panel"):
        st.markdown('<div class="event-heading">Network Inventory</div>', unsafe_allow_html=True)
        st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")

    if visible_bins:
        map_rows = [
            {
                "LAT": item["lat"],
                "LON": item["lon"],
                "Map Size": max(10, item["fill_level"] * 10),
            }
            for item in visible_bins.values()
        ]
        with st.container(border=True, key="bin_network_map_panel"):
            st.markdown('<div class="event-heading">Filtered Bin Locations</div>', unsafe_allow_html=True)
            st.map(pd.DataFrame(map_rows), latitude="LAT", longitude="LON", size="Map Size", color="#46d8ad")
    else:
        st.info("No bins match these filters.")

    with st.container(border=True, key="bin_operations_panel"):
        st.markdown('<div class="event-heading">Bin Operations</div>', unsafe_allow_html=True)
        selected_bin = st.selectbox("Select bin", bin_ids, key="bin_operations_select")
        selected_data = bins[selected_bin]
        st.caption(
            f"{selected_data['status']} · {selected_data['fill_volume_liters']:.1f} L of "
            f"{selected_data['capacity_liters']:.1f} L · {selected_data['sensor_source']} reading"
        )
        with st.form("bin_sensor_update_form"):
            distance_cm = st.number_input(
                "Ultrasonic air gap (cm)",
                min_value=0.0,
                max_value=float(selected_data["bin_height_cm"]),
                value=float(selected_data["ultrasonic_distance_cm"]),
                step=0.5,
            )
            temperature = st.number_input(
                "Temperature (°C)",
                min_value=-20.0,
                max_value=100.0,
                value=float(selected_data["temperature"]),
                step=0.1,
            )
            battery = st.number_input(
                "Battery (%)",
                min_value=0.0,
                max_value=100.0,
                value=float(selected_data["battery"]),
                step=1.0,
            )
            update_reading = st.form_submit_button("Apply sensor reading", type="primary")

        if update_reading:
            twin_system.update_bin_from_ultrasonic(
                selected_bin,
                distance_cm,
                temperature=temperature,
                battery=battery,
                source="Manual entry",
            )
            st.success("Sensor reading applied and bin volume recalculated.")

        action_col, ping_col, mixed_col = st.columns(3)
        with action_col:
            if st.button("Mark emptied", key="mark_bin_emptied", icon=":material/delete_sweep:", width="stretch"):
                twin_system.update_bin_level(selected_bin, 0)
                twin_system.bins[selected_bin]["emptied_at"] = datetime.now().strftime("%H:%M")
                st.session_state.setdefault("mixed_waste_flags", {}).pop(selected_bin, None)
                st.toast(f"{selected_bin.split(' (')[0]} marked as emptied")
                st.rerun()
        with ping_col:
            if st.button("Ping sensor", key="ping_bin_sensor", icon=":material/wifi_tethering:", width="stretch"):
                twin_system.bins[selected_bin]["last_ping_at"] = datetime.now()
                st.toast(f"Sensor ping recorded for {selected_bin.split(' (')[0]}")
        with mixed_col:
            mixed_flags = st.session_state.setdefault("mixed_waste_flags", {})
            if selected_bin in mixed_flags:
                if st.button("Clear mixed flag", key="clear_mixed_flag", icon=":material/check:", width="stretch"):
                    mixed_flags.pop(selected_bin, None)
                    st.toast(f"Mixed-waste report cleared for {selected_bin.split(' (')[0]}")
                    st.rerun()
            elif st.button("Report mixed waste", key="report_mixed_waste", icon=":material/warning:", width="stretch"):
                mixed_flags[selected_bin] = {"reported_at": datetime.now(), "reported_by": "operator"}
                st.toast(f"Mixed-waste report recorded for {selected_bin.split(' (')[0]}")
                st.rerun()