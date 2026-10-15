import streamlit as st


def render_settings_page():
    st.markdown('<div class="page-heading">Settings</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="page-subtitle">Configure operational notifications for this session</div>',
        unsafe_allow_html=True,
    )

    with st.container(border=True, key="operational_alert_settings"):
        st.markdown('<div class="event-heading">Operational Alerts</div>', unsafe_allow_html=True)
        st.toggle(
            "Enable popup alerts",
            value=False,
            key="operational_alerts_enabled",
            help="Show a modal when a bin crosses the fill threshold or is reported as contaminated.",
        )
        st.slider(
            "Full-bin alert threshold (%)",
            min_value=50,
            max_value=100,
            value=85,
            step=5,
            key="full_bin_alert_threshold",
            disabled=not st.session_state.operational_alerts_enabled,
        )
        st.caption(
            "Mixed-waste alerts are based on an operator report in Bin Network. "
            "The current system has no camera or material sensor inside the bins, so it cannot detect mixing automatically."
        )