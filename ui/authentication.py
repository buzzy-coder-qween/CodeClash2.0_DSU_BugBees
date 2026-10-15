import time

import streamlit as st


SESSION_TIMEOUT_SECONDS = 8 * 60 * 60


def render_authentication(auth_service):
    authenticated_user = st.session_state.get("authenticated_user")
    now = time.time()
    if authenticated_user:
        last_activity = st.session_state.get("last_activity_at", now)
        if now - last_activity <= SESSION_TIMEOUT_SECONDS:
            st.session_state.last_activity_at = now
            return True
        st.session_state.pop("authenticated_user", None)
        st.session_state.pop("last_activity_at", None)

    left_column, login_column, right_column = st.columns([1.1, 1, 1.1])
    with login_column:
        st.markdown(
            """
            <div style="text-align:center;padding:24px 0 12px">
              <div style="display:inline-grid;place-items:center;width:48px;height:48px;border-radius:12px;background:#15332b;color:#46d8ad;font-size:25px">♻</div>
              <div style="font-size:22px;font-weight:700;margin-top:12px;color:#e8efed">EcoTwin</div>
              <div style="font-size:12px;color:#7e8b8d;margin-top:4px">Waste Management Digital Twin</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        with st.container(border=True, key="login_panel"):
            st.markdown("### Sign in")
            if auth_service.user_count == 0:
                if auth_service.bootstrap_error:
                    st.error(auth_service.bootstrap_error)
                else:
                    st.info("No administrator account is configured yet. Create the first account from the project terminal.")
                st.code("python -m core.auth create-admin", language="powershell")
                st.caption("This creates the one-time administrator account. No default credentials are enabled.")
                if st.button("Refresh sign-in", key="refresh_auth_setup", width="stretch"):
                    st.rerun()
                return False

            with st.form("login_form", clear_on_submit=False):
                username = st.text_input("Username", max_chars=40)
                password = st.text_input("Password", type="password", max_chars=1024)
                submitted = st.form_submit_button("Sign in", type="primary", width="stretch")
            if submitted:
                user, message = auth_service.authenticate(username, password)
                if user:
                    st.session_state.authenticated_user = user
                    st.session_state.last_activity_at = time.time()
                    st.rerun()
                st.error(message)
    return False