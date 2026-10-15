import streamlit as st
import cv2


def set_active_page(page_name):
    st.session_state.active_page = page_name


def render_sidebar(twin_system, authenticated_user):
    st.sidebar.markdown(
        """
        <div class="brand">
          <div class="brand-mark">♻</div>
          <div><div class="brand-name">EcoTwin</div><div class="brand-sub">Waste Digital Twin</div></div>
        </div>
        <div class="side-label">OPERATIONS</div>
        """,
        unsafe_allow_html=True,
    )

    navigation = [
        ("Overview", ":material/space_dashboard:"),
        ("Waste Segregation", ":material/recycling:"),
        ("Bin Network", ":material/delete_outline:"),
        ("Sensors", ":material/sensors:"),
        ("Analytics", ":material/monitoring:"),
    ]
    for page_name, page_icon in navigation:
        st.sidebar.button(
            page_name,
            key=f"nav_{page_name.lower().replace(' ', '_').replace('&', 'and')}",
            icon=page_icon,
            type="primary" if st.session_state.active_page == page_name else "secondary",
            width="stretch",
            on_click=set_active_page,
            args=(page_name,),
        )

    st.sidebar.markdown('<div class="side-label">SYSTEM</div>', unsafe_allow_html=True)
    st.sidebar.button(
        "Settings",
        icon=":material/settings:",
        type="primary" if st.session_state.active_page == "Settings" else "secondary",
        width="stretch",
        on_click=set_active_page,
        args=("Settings",),
    )
    st.sidebar.caption(f"Signed in as {authenticated_user['username']} · {authenticated_user['role']}")
    if st.sidebar.button("Sign out", icon=":material/logout:", width="stretch"):
        capture = st.session_state.pop("seg_camera_capture", None)
        if capture is not None:
            capture.release()
        for key in ("authenticated_user", "last_activity_at", "seg_camera_active", "seg_live_frame"):
            st.session_state.pop(key, None)
        st.rerun()
    if st.sidebar.button("Simulate sensor update", icon=":material/refresh:", width="stretch"):
        twin_system.simulate_realtime_drift()
        st.toast("Sensor values updated")
    if st.sidebar.button("Simulate waste deposit", icon=":material/delete:", width="stretch"):
        deposit_event = twin_system.simulate_waste_deposit()
        if deposit_event:
            st.session_state["last_deposit_event"] = deposit_event
            # Append to rolling deposit history (keep last 50)
            deposit_history = st.session_state.setdefault("deposit_history", [])
            deposit_history.insert(0, deposit_event)
            st.session_state["deposit_history"] = deposit_history[:50]
            st.toast(
                f"{deposit_event['icon']}  {deposit_event['item_name']} → "
                f"{deposit_event['category']} → {deposit_event['bin_short']}"
            )

