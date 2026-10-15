import os
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

    # ── Google Gemini GenAI Settings ──
    from core.genai import get_api_key, is_genai_available, get_genai_client

    with st.container(border=True, key="genai_settings_card"):
        st.markdown('<div class="event-heading">🤖 Google Gemini Generative AI</div>', unsafe_allow_html=True)
        st.caption("Powers AI collection routing, waste segregation advice, and the EcoTwin Copilot.")

        active_key = get_api_key()
        has_key = is_genai_available()

        if has_key:
            st.success("🟢 Google Gemini is connected and active.", icon=":material/check_circle:")
        else:
            st.warning(
                "🟡 No Gemini API key detected. The system is running in offline simulation mode.",
                icon=":material/info:",
            )

        api_input = st.text_input(
            "Gemini API Key",
            value=active_key if active_key else "",
            type="password",
            placeholder="AIzaSy...",
            help="Get a free key from Google AI Studio: https://aistudio.google.com/app/apikey",
        )

        key_col1, key_col2 = st.columns([1, 1], gap="small")
        with key_col1:
            if st.button("Save & Activate Key", icon=":material/save:", type="primary", width="stretch"):
                if api_input.strip():
                    st.session_state.gemini_api_key = api_input.strip()
                    # Also append or update in .env for persistence
                    try:
                        env_path = ".env"
                        env_content = ""
                        if os.path.exists(env_path):
                            with open(env_path, "r", encoding="utf-8") as f:
                                env_content = f.read()
                        if "GEMINI_API_KEY=" in env_content:
                            import re
                            new_env = re.sub(r"GEMINI_API_KEY=.*", f"GEMINI_API_KEY={api_input.strip()}", env_content)
                        else:
                            new_env = env_content.rstrip() + f"\nGEMINI_API_KEY={api_input.strip()}\n"
                        with open(env_path, "w", encoding="utf-8") as f:
                            f.write(new_env)
                    except Exception as env_err:
                        print(f"Could not persist to .env: {env_err}")

                    st.toast("Gemini API Key saved and activated!")
                    st.rerun()
                else:
                    st.error("Please enter a valid API key.")

        with key_col2:
            if st.button("Test Connection", icon=":material/electrical_services:", width="stretch", disabled=not (api_input.strip() or has_key)):
                test_key = api_input.strip() or active_key
                try:
                    from google import genai
                    test_client = genai.Client(api_key=test_key)
                    with st.spinner("Connecting to Google Gemini..."):
                        test_resp = test_client.models.generate_content(
                            model="gemini-2.5-flash",
                            contents="Respond with the word 'Connected' if you can read this.",
                        )
                        st.toast(f"✅ Gemini Response: {test_resp.text.strip()}")
                        st.session_state.gemini_api_key = test_key
                except Exception as test_err:
                    st.error(f"Failed to connect to Gemini: {test_err}")