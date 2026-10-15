import cv2
import streamlit as st


@st.fragment(run_every=0.5)
def show_segregation_camera():
    capture = st.session_state.get("seg_camera_capture")
    if capture is None or not capture.isOpened():
        st.error("Camera unavailable. Check device permissions and try again.")
        return

    frame_read, frame = capture.read()
    if not frame_read:
        st.warning("The camera is open, but no frame could be read.")
        return

    st.session_state.seg_live_frame = frame.copy()
    st.image(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB), channels="RGB", width="stretch")