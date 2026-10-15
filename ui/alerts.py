import streamlit as st


@st.dialog("Waste Operations Alert", width="large")
def _show_alert_dialog(alerts, alert_signature):
    st.markdown("Review these active bin conditions:")
    for alert in alerts:
        if alert["kind"] == "full":
            st.error(f"**Full bin · {alert['bin_id']}**\n\n{alert['message']}")
        else:
            st.warning(f"**Mixed waste reported · {alert['bin_id']}**\n\n{alert['message']}")

    if st.button("Acknowledge alerts", key="acknowledge_operational_alerts", type="primary"):
        st.session_state.acknowledged_alert_signature = alert_signature
        st.rerun()


def collect_operational_alerts(twin_system, mixed_waste_flags, threshold):
    alerts = []
    for bin_id, bin_data in twin_system.get_all_bins().items():
        if bin_data["fill_level"] >= threshold:
            alerts.append(
                {
                    "kind": "full",
                    "bin_id": bin_id,
                    "key": f"full:{bin_id}",
                    "message": (
                        f"Estimated fill is {bin_data['fill_level']:.1f}% "
                        f"({bin_data['fill_volume_liters']:.1f} L of {bin_data['capacity_liters']:.1f} L)."
                    ),
                }
            )

    for bin_id, report in mixed_waste_flags.items():
        if report:
            alerts.append(
                {
                    "kind": "mixed",
                    "bin_id": bin_id,
                    "key": f"mixed:{bin_id}",
                    "message": "An operator reported that the contents may contain more than one waste stream. Inspect and re-sort as needed.",
                }
            )
    return alerts


def show_operational_alerts(twin_system):
    if not st.session_state.get("operational_alerts_enabled", False):
        st.session_state.active_alert_signature = ()
        st.session_state.acknowledged_alert_signature = ()
        return

    threshold = st.session_state.get("full_bin_alert_threshold", 85)
    mixed_waste_flags = st.session_state.get("mixed_waste_flags", {})
    alerts = collect_operational_alerts(twin_system, mixed_waste_flags, threshold)
    alert_signature = tuple(sorted(alert["key"] for alert in alerts))
    previous_signature = st.session_state.get("active_alert_signature", ())
    if alert_signature != previous_signature:
        st.session_state.active_alert_signature = alert_signature
        st.session_state.acknowledged_alert_signature = ()

    if alerts and alert_signature != st.session_state.get("acknowledged_alert_signature", ()):
        _show_alert_dialog(alerts, alert_signature)