from datetime import datetime, timedelta
from html import escape
from textwrap import dedent

import cv2
import json
import numpy as np
import pandas as pd
import streamlit as st

from core.twin import SmartBinSystem
from core.auth import AuthService
from core.waste_taxonomy import get_ewaste_model_path, get_waste_model_path
from ui.alerts import show_operational_alerts
from ui.analytics import render_analytics_page
from ui.authentication import render_authentication
from ui.bin_network import render_bin_network_page
from ui.camera import show_segregation_camera
from ui.navigation import render_sidebar
from ui.sensors import render_sensors_page
from ui.settings import render_settings_page

st.set_page_config(page_title="EcoTwin | Waste Network Overview", layout="wide")

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500;600&display=swap');
    :root {
        --canvas: #080c0d;
        --sidebar: #0b1011;
        --panel: #111719;
        --panel-raised: #151d1f;
        --line: #222c2e;
        --text: #e8efed;
        --muted: #7e8b8d;
        --mint: #46d8ad;
        --red: #f16d75;
        --amber: #e8bd5e;
    }
    html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }
    [data-testid="stAppViewContainer"] { background: var(--canvas); color: var(--text); }
    [data-testid="stHeader"] { background: transparent; }
    section[data-testid="stSidebar"] { width: 235px !important; min-width: 235px !important; background: var(--sidebar); border-right: 1px solid #1c2527; }
    section[data-testid="stSidebar"] > div:first-child { padding-top: .25rem; }
    section[data-testid="stSidebar"] [data-testid="stSidebarUserContent"] { padding-top: .4rem; }
    section[data-testid="stSidebar"] [data-testid="stVerticalBlock"] { gap: .45rem; }
    .block-container { max-width: 1680px; padding: .8rem 1.25rem 1.4rem; }
    [data-testid="stVerticalBlockBorderWrapper"] {
        background: var(--panel); border: 1px solid var(--line); border-radius: 10px;
    }
    [class*="st-key-bin_card_"] [data-testid="stVerticalBlockBorderWrapper"] { padding: .65rem !important; }
    [class*="st-key-bin_card_"] [data-testid="stVerticalBlock"] { gap: .45rem !important; }
    [data-testid="stBaseButton-primary"] {
        background: #3ed1a5; border-color: #3ed1a5; color: #06221b;
        font-weight: 700; border-radius: 6px; min-height: 32px; padding-top: 4px; padding-bottom: 4px;
    }
    [data-testid="stBaseButton-primary"]:hover { background: #64e4bd; border-color: #64e4bd; color: #06221b; }
    [data-testid="stBaseButton-secondary"] {
        background: #182023; border-color: #283235; color: #c4cecc; border-radius: 6px;
        min-height: 32px; padding-top: 4px; padding-bottom: 4px;
    }
    [data-testid="stBaseButton-secondary"]:hover { border-color: #4d6a65; color: #e8efed; }
    [data-testid="stSidebar"] [data-testid="stBaseButton-secondary"] {
        background: transparent; border-color: transparent; color: #899597; justify-content: flex-start;
    }
    [data-testid="stSidebar"] [data-testid="stBaseButton-primary"] {
        background: #172522; border-color: #213a34; color: var(--mint); justify-content: flex-start;
    }
    [data-testid="stDataFrame"] { border: 1px solid var(--line); border-radius: 7px; overflow: hidden; }
    .brand { display:flex; align-items:center; gap:10px; padding: 4px 4px 22px; }
    .brand-mark { width:34px; height:34px; display:grid; place-items:center; border-radius:9px; background:#15332b; color:var(--mint); font-size:19px; }
    .brand-name { color:var(--text); font-size:15px; line-height:1.1; font-weight:700; }
    .brand-sub { color:var(--muted); font-size:10px; margin-top:4px; }
    .side-label { color:#647173; font-size:10px; font-weight:700; letter-spacing:1px; margin: 12px 0 8px; }
    .page-heading { color:var(--text); font-size:19px; font-weight:700; line-height:1.2; }
    .page-subtitle { color:var(--muted); font-size:12px; margin-top:5px; }
    .top-stats { display:flex; align-items:stretch; justify-content:flex-end; gap:8px; }
    .top-stat { min-width:76px; padding:8px 11px; background:#111719; border:1px solid var(--line); border-radius:7px; }
    .top-stat-label { color:#7e8a8c; font-size:9px; font-weight:700; letter-spacing:.7px; }
    .top-stat-value { color:#e5ecea; font:600 16px 'IBM Plex Mono',monospace; margin-top:3px; }
    .top-stat-value.critical { color:var(--red); }
    .top-stat-value.warning { color:var(--amber); }
    .live-indicator { display:flex; align-items:center; gap:7px; padding:0 12px; border:1px solid var(--line); border-radius:7px; color:#c9d2d0; font-size:12px; white-space:nowrap; }
    .live-dot { width:7px; height:7px; background:var(--mint); border-radius:50%; box-shadow:0 0 10px #46d8ad88; }
    .section-title { color:var(--text); font-size:15px; font-weight:700; margin: 8px 0 2px; }
    .section-note { color:var(--muted); font-size:11px; }
    .bin-code { color:#859193; font: 10px 'IBM Plex Mono',monospace; }
    .bin-name { color:#edf3f1; font-size:14px; font-weight:600; margin-top:3px; }
    .bin-location { color:#778486; font-size:9px; margin-top:2px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
    .bin-card-head { display:flex; justify-content:space-between; gap:8px; align-items:flex-start; }
    .status-chip { border-radius:20px; padding:3px 8px; font-size:9px; font-weight:700; white-space:nowrap; }
    .status-chip.critical { color:#ff9399; background:#3a2226; }
    .status-chip.warning { color:#f0ca72; background:#392f1b; }
    .status-chip.normal { color:#6fe0bb; background:#18352d; }
    .fill-row { display:flex; align-items:flex-end; justify-content:space-between; margin:9px 0 5px; }
    .fill-label { color:#809092; font-size:9px; font-weight:700; letter-spacing:.7px; }
    .fill-value { font:600 24px 'IBM Plex Mono',monospace; line-height:1; }
    .fill-value.critical { color:var(--red); }
    .fill-value.warning { color:var(--amber); }
    .fill-value.normal { color:#56dcb3; }
    .waste-tag { color:#bac4c2; font-size:9px; background:#20282a; padding:4px 7px; border-radius:5px; }
    .progress-track { height:6px; background:#20282a; border-radius:8px; overflow:hidden; }
    .progress-fill { height:100%; border-radius:8px; }
    .progress-fill.critical { background:var(--red); }
    .progress-fill.warning { background:var(--amber); }
    .progress-fill.normal { background:#49d7ad; }
    .bin-meta { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:5px; margin-top:8px; }
    .meta-cell { min-width:0; background:#0d1314; border-radius:5px; padding:5px 6px; }
    .meta-label { color:#758183; font-size:8px; }
    .meta-value { color:#d7e0de; font: 10px 'IBM Plex Mono',monospace; margin-top:4px; white-space:nowrap; }
    .route-title { font-size:15px; font-weight:700; color:var(--text); }
    .route-subtitle { font-size:10px; color:var(--muted); margin-top:3px; }
    .route-copy { min-height:205px; padding:13px; margin:15px 0 10px; background:#0c1213; border:1px solid #20292b; border-radius:7px; color:#aab5b3; font:11px/1.7 'IBM Plex Mono',monospace; white-space:pre-wrap; }
    .route-kicker { color:#5bdec0; font:700 9px 'IBM Plex Mono',monospace; letter-spacing:.5px; margin-bottom:9px; }
    .event-heading { color:var(--text); font-size:15px; font-weight:700; }
    .event-caption { color:var(--muted); font-size:10px; margin-top:3px; }
    .seg-stat-row { display:flex; justify-content:flex-end; gap:7px; }
    .seg-stat { min-width:82px; padding:7px 10px; background:#111719; border:1px solid var(--line); border-radius:7px; }
    .seg-stat-label { color:#7e8a8c; font-size:8px; font-weight:700; letter-spacing:.7px; }
    .seg-stat-value { color:#e5ecea; font:600 14px 'IBM Plex Mono',monospace; margin-top:3px; }
    .seg-camera-head { display:flex; align-items:center; justify-content:space-between; }
    .seg-title { color:var(--text); font-size:14px; font-weight:700; }
    .seg-caption { color:var(--muted); font-size:10px; margin-top:3px; }
    .seg-offline { color:#8a9698; border:1px solid #293234; border-radius:20px; padding:4px 9px; font-size:9px; }
    .seg-preview { min-height:250px; aspect-ratio: 2.4 / 1; display:flex; flex-direction:column; align-items:center; justify-content:center; gap:9px; margin:12px 0 10px; background:#090e0f; border:1px solid #20292b; border-radius:8px; color:#748183; text-align:center; }
    .seg-preview-icon { color:#778486; font-size:28px; }
    .seg-preview-copy { font-size:11px; }
    .seg-flow { display:flex; gap:12px; justify-content:flex-end; color:#718082; font:9px 'IBM Plex Mono',monospace; }
    .seg-flow .done { color:#4bd9ad; }
    .seg-bin-grid { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:10px; }
    .seg-bin-card { min-width:0; padding:12px; background:#111719; border:1px solid #222c2e; border-radius:9px; }
    .seg-bin-top { display:flex; align-items:center; justify-content:space-between; gap:8px; }
    .seg-bin-icon { display:grid; place-items:center; width:26px; height:26px; border-radius:7px; font-size:14px; }
    .seg-bin-id { color:#849092; font:9px 'IBM Plex Mono',monospace; }
    .seg-bin-name { color:#e8efed; font-size:12px; font-weight:700; margin-top:8px; }
    .seg-bin-desc { color:#879395; font-size:9px; min-height:23px; margin-top:3px; }
    .seg-bin-progress { position:relative; height:44px; margin-top:7px; background:#090e0f; border:1px solid #20292b; border-radius:6px; overflow:hidden; }
    .seg-bin-fill { position:absolute; inset:auto 0 0; opacity:.55; }
    .seg-bin-percent { position:absolute; top:5px; right:7px; color:#b9c4c2; font:9px 'IBM Plex Mono',monospace; }
    .seg-bin-count { color:#aab5b3; font:9px 'IBM Plex Mono',monospace; margin-top:6px; }
    .seg-detection { color:#d6dfdd; font-size:11px; }
    .seg-detection strong { color:#4cdbb0; }
    @media (max-width: 760px) {
        .seg-bin-grid { grid-template-columns:repeat(2,minmax(0,1fr)); }
        .seg-preview { min-height:180px; aspect-ratio: 1.5 / 1; }
        .seg-stat-row { justify-content:flex-start; flex-wrap:wrap; margin-top:10px; }
    }
    @media (max-width: 900px) {
        section[data-testid="stSidebar"] { width: 235px !important; min-width: 235px !important; }
        .block-container { padding: .8rem .8rem 1.5rem; }
        .top-stats { justify-content:flex-start; flex-wrap:wrap; margin-top:12px; }
        .top-stat { min-width:65px; }
        .live-indicator { min-height:40px; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

auth_service = AuthService()
if not render_authentication(auth_service):
    st.stop()
authenticated_user = st.session_state.authenticated_user


def classify_segregation_frame(frame):
    from core.vision import WasteDetector

    if "seg_detector" not in st.session_state or not st.session_state.seg_detector.is_current():
        st.session_state.seg_detector = WasteDetector()

    annotated_frame, detection = st.session_state.seg_detector.detect_waste(frame, confidence_threshold=0.2)
    if detection is None:
        return None
    return {
        "frame": annotated_frame,
        "class_name": detection["label"],
        "category": detection["category"],
        "confidence": detection["confidence"],
    }


def render_waste_segregation_page():
    if "seg_bins" not in st.session_state:
        st.session_state.seg_bins = [
            {"name": "Recyclables", "id": "SEG-01", "description": "Plastic bottles, cans, glass jars", "icon": "♻", "color": "#24a8d1", "count": 9, "capacity": 24},
            {"name": "Paper & Card", "id": "SEG-02", "description": "Cardboard, newspaper, cartons", "icon": "▤", "color": "#b58a37", "count": 6, "capacity": 24},
            {"name": "Organic", "id": "SEG-03", "description": "Food scraps, peels, garden waste", "icon": "◉", "color": "#11a982", "count": 11, "capacity": 20},
            {"name": "E-Waste", "id": "SEG-04", "description": "Phones, cables, chargers, PCBs", "icon": "⌘", "color": "#8b65bd", "count": 2, "capacity": 12},
            {"name": "Hazardous", "id": "SEG-05", "description": "Batteries, paint, chemicals, bulbs", "icon": "⚠", "color": "#bd4654", "count": 1, "capacity": 10},
            {"name": "Landfill", "id": "SEG-06", "description": "Chip bags, diapers, ceramics", "icon": "▣", "color": "#657177", "count": 7, "capacity": 20},
        ]
    st.session_state.setdefault("seg_sorted_today", 36)
    st.session_state.setdefault("seg_diverted_count", 29)
    st.session_state.setdefault("seg_log", [])
    st.session_state.setdefault("seg_classification", None)
    st.session_state.setdefault("seg_classification_attempted", False)
    st.session_state.setdefault("seg_input_frame", None)
    st.session_state.setdefault("seg_input_name", "")
    st.session_state.setdefault("seg_camera_active", False)

    title_col, stats_col = st.columns([1.3, 1], vertical_alignment="center")
    with title_col:
        st.markdown('<div class="page-heading">Waste Segregation Station</div>', unsafe_allow_html=True)
        st.markdown('<div class="page-subtitle">AI vision sorting · Capture an item to route it to the right bin</div>', unsafe_allow_html=True)
    with stats_col:
        diverted_percent = round(st.session_state.seg_diverted_count / max(1, st.session_state.seg_sorted_today) * 100)
        st.markdown(
            f"""
            <div class="seg-stat-row">
              <div class="seg-stat"><div class="seg-stat-label">SORTED TODAY</div><div class="seg-stat-value">{st.session_state.seg_sorted_today}</div></div>
              <div class="seg-stat"><div class="seg-stat-label">DIVERTED</div><div class="seg-stat-value">{diverted_percent}%</div></div>
              <div class="seg-stat"><div class="seg-stat-label">SESSION</div><div class="seg-stat-value">{len(st.session_state.seg_log)}</div></div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    waste_model_path = get_waste_model_path()
    ewaste_model_path = get_ewaste_model_path()
    if not waste_model_path.is_file():
        st.warning("Core waste-stream weights are not trained yet. The station is using generic COCO demo weights for non-electronic waste.")
    else:
        metadata_path = waste_model_path.with_suffix(".metadata.json")
        if not metadata_path.is_file():
            st.warning("Waste-specific weights were found, but class-coverage metadata is missing. Validate every stream before use.")
        else:
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            unsupported_streams = metadata.get("unsupported_classes", [])
            if ewaste_model_path.is_file():
                unsupported_streams = [stream for stream in unsupported_streams if stream != "E-Waste"]
        if metadata_path.is_file() and unsupported_streams:
            st.warning(f"Waste model has no training examples for: {', '.join(unsupported_streams)}. Those streams are not validated.")
        elif metadata_path.is_file():
            st.success("Fine-tuned waste-specific model is active.")
    if ewaste_model_path.is_file():
        ewaste_metadata_path = ewaste_model_path.with_suffix(".metadata.json")
        if ewaste_metadata_path.is_file():
            ewaste_metadata = json.loads(ewaste_metadata_path.read_text(encoding="utf-8"))
            st.success(
                f"Dedicated e-waste model active · validation mAP50 "
                f"{ewaste_metadata.get('validation_map50', 0):.3f}."
            )
        else:
            st.warning("E-waste weights are installed, but validation metadata is missing.")
    else:
        st.warning("Dedicated e-waste weights are not installed. Set ROBOFLOW_API_KEY in .env, then run the training command in datasets/README.md.")

    with st.container(border=True, key="seg_intake_panel"):
        st.markdown(
            f"""
            <div class="seg-camera-head"><div><div class="seg-title">Intake Camera</div>
            <div class="seg-caption">Station SEG-A · Conveyor intake</div></div>
            <span class="seg-offline">● {'LIVE' if st.session_state.seg_camera_active else 'OFFLINE'}</span></div>
            """,
            unsafe_allow_html=True,
        )
        camera_col, capture_col, upload_col = st.columns([1.05, 1, 2.2], gap="small", vertical_alignment="bottom")
        with camera_col:
            start_label = "Stop camera" if st.session_state.seg_camera_active else "Start camera"
            if st.button(start_label, key="seg_start_camera", icon=":material/videocam:", type="primary" if not st.session_state.seg_camera_active else "secondary", width="stretch"):
                if st.session_state.seg_camera_active:
                    capture = st.session_state.pop("seg_camera_capture", None)
                    if capture is not None:
                        capture.release()
                    st.session_state.seg_camera_active = False
                else:
                    capture = cv2.VideoCapture(0)
                    if capture.isOpened():
                        st.session_state.seg_camera_capture = capture
                        st.session_state.seg_camera_active = True
                    else:
                        capture.release()
                        st.error("Could not start the webcam. Check camera permissions and close other camera apps.")
                st.rerun()
        with capture_col:
            if st.button("Capture frame", key="seg_capture_frame", icon=":material/photo_camera:", disabled=not st.session_state.seg_camera_active, width="stretch"):
                live_frame = st.session_state.get("seg_live_frame")
                if live_frame is not None:
                    st.session_state.seg_input_frame = live_frame.copy()
                    st.session_state.seg_input_name = "Camera capture"
                    st.session_state.seg_classification = None
                    st.session_state.seg_classification_attempted = False
                capture = st.session_state.pop("seg_camera_capture", None)
                if capture is not None:
                    capture.release()
                st.session_state.seg_camera_active = False
                st.rerun()
        with upload_col:
            uploaded_photo = st.file_uploader("Upload photo", type=["jpg", "jpeg", "png", "webp"], key="seg_photo_upload", label_visibility="collapsed")
            if uploaded_photo is not None:
                uploaded_frame = cv2.imdecode(np.frombuffer(uploaded_photo.getvalue(), dtype=np.uint8), cv2.IMREAD_COLOR)
                if uploaded_frame is not None:
                    st.session_state.seg_input_frame = uploaded_frame
                    st.session_state.seg_input_name = uploaded_photo.name
                    st.session_state.seg_classification = None
                    st.session_state.seg_classification_attempted = False
                    if st.session_state.seg_camera_active:
                        capture = st.session_state.pop("seg_camera_capture", None)
                        if capture is not None:
                            capture.release()
                        st.session_state.seg_camera_active = False

        if st.session_state.seg_camera_active:
            show_segregation_camera()
        elif st.session_state.seg_input_frame is not None:
            st.image(
                cv2.cvtColor(st.session_state.seg_input_frame, cv2.COLOR_BGR2RGB),
                caption=st.session_state.seg_input_name,
                channels="RGB",
                width="stretch",
            )
        else:
            st.markdown(
                '<div class="seg-preview"><div class="seg-preview-icon">▧</div><div class="seg-preview-copy">Start the camera or upload a photo of a waste item to begin sorting.</div></div>',
                unsafe_allow_html=True,
            )

    with st.container(border=True, key="seg_detection_panel"):
        detection_header, detection_flow = st.columns([1, 1], vertical_alignment="center")
        with detection_header:
            st.markdown('<div class="seg-title">✦ AI Detection</div><div class="seg-caption">Captured items are identified by a vision model, then routed to the matching segregation bin.</div>', unsafe_allow_html=True)
        with detection_flow:
            st.markdown(
                f'<div class="seg-flow"><span class="{"done" if st.session_state.seg_input_frame is not None else ""}">Capture</span><span class="{"done" if st.session_state.seg_classification else ""}">Classify</span><span class="{"done" if st.session_state.seg_log and st.session_state.seg_classification is None else ""}">Sort</span></div>',
                unsafe_allow_html=True,
            )
        classify_col, sort_col = st.columns([1, 1], gap="small")
        with classify_col:
            if st.button("Classify item", key="seg_classify", icon=":material/auto_awesome:", disabled=st.session_state.seg_input_frame is None, width="stretch"):
                with st.spinner("Analyzing image with YOLOv8..."):
                    st.session_state.seg_classification = classify_segregation_frame(st.session_state.seg_input_frame)
                    st.session_state.seg_classification_attempted = True
        classification = st.session_state.seg_classification
        with sort_col:
            if st.button("Sort item", key="seg_sort", icon=":material/move_to_inbox:", type="primary", disabled=classification is None, width="stretch"):
                selected_bin = next(item for item in st.session_state.seg_bins if item["name"] == classification["category"])
                selected_bin["count"] = min(selected_bin["capacity"], selected_bin["count"] + 1)
                st.session_state.seg_sorted_today += 1
                if selected_bin["name"] != "Landfill":
                    st.session_state.seg_diverted_count += 1
                st.session_state.seg_log.insert(
                    0,
                    {
                        "TIME": datetime.now().strftime("%H:%M:%S"),
                        "ITEM": classification["class_name"].title(),
                        "ROUTED TO": selected_bin["name"],
                        "CONFIDENCE": f"{classification['confidence']:.0%}",
                    },
                )
                st.session_state.seg_log = st.session_state.seg_log[:20]
                st.session_state.seg_classification = None
                st.session_state.seg_classification_attempted = False
                st.session_state.seg_input_frame = None
                st.session_state.seg_input_name = ""
                st.rerun()
        if classification:
            st.markdown(
                f'<div class="seg-detection">Detected <strong>{escape(classification["class_name"].title())}</strong> · Suggested bin <strong>{escape(classification["category"])}</strong> · Confidence {classification["confidence"]:.0%}</div>',
                unsafe_allow_html=True,
            )
            st.image(cv2.cvtColor(classification["frame"], cv2.COLOR_BGR2RGB), channels="RGB", width="stretch")
        elif st.session_state.seg_input_frame is None:
            st.caption("Capture or upload an item, then classify it to enable sorting.")
        elif st.session_state.seg_classification_attempted:
            st.warning("No supported waste object was detected. Try a clearer image or capture the item closer.")
        else:
            st.caption("Ready to classify the item.")

    st.markdown('<div class="section-title">Segregation Bins</div>', unsafe_allow_html=True)
    bin_cards = []
    for segregation_bin in st.session_state.seg_bins:
        percent_full = round(segregation_bin["count"] / segregation_bin["capacity"] * 100)
        bin_cards.append(
            dedent(f"""
            <div class="seg-bin-card">
              <div class="seg-bin-top"><div class="seg-bin-icon" style="background:{segregation_bin['color']}22;color:{segregation_bin['color']}">{segregation_bin['icon']}</div><div class="seg-bin-id">{segregation_bin['id']}</div></div>
              <div class="seg-bin-name">{escape(segregation_bin['name'])}</div>
              <div class="seg-bin-desc">{escape(segregation_bin['description'])}</div>
              <div class="seg-bin-progress"><div class="seg-bin-percent">{percent_full}%</div><div class="seg-bin-fill" style="height:{percent_full}%;background:{segregation_bin['color']}"></div></div>
              <div class="seg-bin-count">{segregation_bin['count']} / {segregation_bin['capacity']} items</div>
            </div>
            """).strip()
        )
    st.markdown(f'<div class="seg-bin-grid">{"".join(bin_cards)}</div>', unsafe_allow_html=True)

    with st.container(border=True, key="seg_sort_log"):
        log_header, log_count = st.columns([1, 1], vertical_alignment="center")
        with log_header:
            st.markdown('<div class="event-heading">Sorting Log</div>', unsafe_allow_html=True)
        with log_count:
            st.markdown(f'<div style="text-align:right;color:#899597;font:10px \'IBM Plex Mono\',monospace">{len(st.session_state.seg_log)} items this session</div>', unsafe_allow_html=True)
        if st.session_state.seg_log:
            st.dataframe(pd.DataFrame(st.session_state.seg_log), hide_index=True, width="stretch", height=190)
        else:
            st.markdown('<div class="event-caption">No items sorted yet this session.</div>', unsafe_allow_html=True)


if "twin_system" not in st.session_state:
    st.session_state.twin_system = SmartBinSystem()
default_bins = SmartBinSystem().get_all_bins()
if not hasattr(st.session_state.twin_system, "history"):
    st.session_state.twin_system.history = []
for bin_id, default_details in default_bins.items():
    current_details = st.session_state.twin_system.bins.setdefault(bin_id, default_details.copy())
    has_ultrasonic_reading = "ultrasonic_distance_cm" in current_details
    previous_fill = float(current_details.get("fill_level", default_details["fill_level"]))
    sensor_source = current_details.get(
        "sensor_source",
        "Simulated" if has_ultrasonic_reading else "Migrated estimate",
    )
    for field_name, default_value in default_details.items():
        current_details.setdefault(field_name, default_value)
    if not has_ultrasonic_reading:
        current_details["ultrasonic_distance_cm"] = current_details["bin_height_cm"] * (1 - previous_fill / 100)
    st.session_state.twin_system.update_bin_from_ultrasonic(
        bin_id,
        current_details["ultrasonic_distance_cm"],
        source=sensor_source,
        record=False,
    )
if not st.session_state.twin_system.history:
    st.session_state.twin_system._record_history()
if "active_page" not in st.session_state:
    st.session_state.active_page = "Overview"
if st.session_state.active_page == "Alerts":
    st.session_state.active_page = "Settings"
st.session_state.setdefault("operational_alerts_enabled", False)
st.session_state.setdefault("full_bin_alert_threshold", 85)
st.session_state.setdefault("mixed_waste_flags", {})
render_sidebar(st.session_state.twin_system, authenticated_user)

if st.session_state.active_page != "Waste Segregation":
    segregation_capture = st.session_state.pop("seg_camera_capture", None)
    if segregation_capture is not None:
        segregation_capture.release()
    st.session_state.seg_camera_active = False

bin_data = st.session_state.twin_system.get_all_bins()
bin_rows = [{"Bin ID": bin_id, **details} for bin_id, details in bin_data.items()]
bins_df = pd.DataFrame(bin_rows)
average_fill = round(bins_df["fill_level"].mean()) if not bins_df.empty else 0
critical_count = int((bins_df["fill_level"] >= 85).sum()) if not bins_df.empty else 0
warning_count = int(((bins_df["fill_level"] >= 70) & (bins_df["fill_level"] < 85)).sum()) if not bins_df.empty else 0
show_operational_alerts(st.session_state.twin_system)

if st.session_state.active_page == "Waste Segregation":
    render_waste_segregation_page()
elif st.session_state.active_page == "Sensors":
    render_sensors_page(st.session_state.twin_system)
elif st.session_state.active_page == "Analytics":
    render_analytics_page(st.session_state.twin_system)
elif st.session_state.active_page == "Bin Network":
    render_bin_network_page(st.session_state.twin_system)
elif st.session_state.active_page == "Settings":
    render_settings_page()
elif st.session_state.active_page != "Overview":
    st.markdown(f'<div class="page-heading">{escape(st.session_state.active_page)}</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-subtitle">Waste network operations</div>', unsafe_allow_html=True)
    if st.session_state.active_page == "City Map":
        map_df = bins_df.rename(columns={"lat": "LAT", "lon": "LON", "fill_level": "Fill Level"})
        map_df["Map Size"] = map_df["Fill Level"] * 10
        st.map(map_df, latitude="LAT", longitude="LON", size="Map Size", color="#46d8ad")
    else:
        st.info(f"{st.session_state.active_page} view is ready for the next build step.")
else:
    title_col, status_col = st.columns([1.65, 1], vertical_alignment="center")
    with title_col:
        st.markdown('<div class="page-heading">Waste Network Overview</div>', unsafe_allow_html=True)
        st.markdown(
            f'<div class="page-subtitle">Metro district · Digital twin of {len(bin_data)} smart bins</div>',
            unsafe_allow_html=True,
        )
    with status_col:
        st.markdown(
            f"""
            <div class="top-stats">
              <div class="top-stat"><div class="top-stat-label">AVG. FILL</div><div class="top-stat-value">{average_fill}%</div></div>
              <div class="top-stat"><div class="top-stat-label">CRITICAL</div><div class="top-stat-value critical">{critical_count}</div></div>
              <div class="top-stat"><div class="top-stat-label">WARNING</div><div class="top-stat-value warning">{warning_count}</div></div>
              <div class="live-indicator"><span class="live-dot"></span>Live</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown('<div class="section-title">Bin Status</div>', unsafe_allow_html=True)
    left_panel, route_panel = st.columns([2.1, 0.95], gap="medium")
    with left_panel:
        for row_start in range(0, len(bin_rows), 2):
            card_columns = st.columns(2, gap="small")
            for card_column, bin_row in zip(card_columns, bin_rows[row_start : row_start + 2]):
                bin_id, _, location = bin_row["Bin ID"].partition(" (")
                location = location.rstrip(")") or bin_id
                fill_level = int(bin_row["fill_level"])
                severity = "critical" if fill_level >= 85 else "warning" if fill_level >= 70 else "normal"
                severity_label = "Critical" if severity == "critical" else "Warning" if severity == "warning" else "Normal"
                with card_column:
                    with st.container(border=True, key=f"bin_card_{bin_id.lower().replace('-', '_')}"):
                        st.markdown(
                            f"""
                            <div class="bin-card-head">
                              <div>
                                <div class="bin-code">{escape(bin_id)}</div>
                                <div class="bin-name">{escape(location)}</div>
                                <div class="bin-location">Campus district · {bin_row['lat']:.4f}, {bin_row['lon']:.4f}</div>
                              </div>
                              <span class="status-chip {severity}">{severity_label}</span>
                            </div>
                            <div class="fill-row">
                              <div><div class="fill-label">FILL LEVEL</div><div class="fill-value {severity}">{fill_level}<span style="font-size:13px">%</span></div></div>
                              <span class="waste-tag">{escape(str(bin_row['type']))}</span>
                            </div>
                            <div class="progress-track"><div class="progress-fill {severity}" style="width:{max(0, min(100, fill_level))}%"></div></div>
                            <div class="bin-meta">
                              <div class="meta-cell"><div class="meta-label">TEMP</div><div class="meta-value">{bin_row['temperature']:.1f}°C</div></div>
                              <div class="meta-cell"><div class="meta-label">BATTERY</div><div class="meta-value">{bin_row['battery']}%</div></div>
                              <div class="meta-cell"><div class="meta-label">EMPTIED</div><div class="meta-value">{escape(str(bin_row['emptied_at']))}</div></div>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )
                        dispatch_col, ping_col = st.columns([1.35, 1], gap="small")
                        with dispatch_col:
                            if st.button(
                                "Dispatch",
                                key=f"dispatch_{bin_id.lower().replace('-', '_')}",
                                icon=":material/local_shipping:",
                                type="primary" if severity == "critical" else "secondary",
                                width="stretch",
                            ):
                                st.session_state.twin_system.update_bin_level(bin_row["Bin ID"], 0)
                                st.toast(f"{bin_id} marked for servicing")
                                st.rerun()
                        with ping_col:
                            if st.button(
                                "Ping",
                                key=f"ping_{bin_id.lower().replace('-', '_')}",
                                width="stretch",
                            ):
                                st.toast(f"Signal received from {bin_id}")

    with route_panel:
        with st.container(border=True, key="route_recommendations"):
            st.markdown(
                '<div class="route-title">AI Routing Recommendations</div><div class="route-subtitle">Collection plan from current fill levels and bin health</div>',
                unsafe_allow_html=True,
            )
            if st.session_state.get("route_plan"):
                plan_text = st.session_state.route_plan
            else:
                plan_text = (
                    "No route generated yet.\n\n"
                    "Generate a plan to prioritize bins by overflow risk, then remaining fill level."
                )
            st.markdown(
                f'<div class="route-copy"><div class="route-kicker">ROUTE PREVIEW</div>{escape(plan_text)}</div>',
                unsafe_allow_html=True,
            )
            if st.button("Plan route", key="generate_route", icon=":material/route:", type="primary", width="stretch"):
                priority_bins = sorted(bin_rows, key=lambda item: item["fill_level"], reverse=True)
                route_lines = ["Suggested collection order", ""]
                route_lines.extend(
                    f"{index}. {item['Bin ID']}  ·  {item['fill_level']}% full"
                    for index, item in enumerate(priority_bins, start=1)
                )
                route_lines.extend(["", "Critical bins are serviced first."])
                st.session_state.route_plan = "\n".join(route_lines)
                st.rerun()

    now = datetime.now()
    event_rows = []
    for event_index, item in enumerate(sorted(bin_rows, key=lambda bin_item: bin_item["fill_level"], reverse=True)):
        is_critical = item["fill_level"] >= 85
        event_rows.append(
            {
                "TIME": (now - timedelta(minutes=event_index * 3)).strftime("%H:%M:%S"),
                "BIN": item["Bin ID"].split(" (")[0],
                "EVENT": "Fill threshold exceeded" if is_critical else "Sensor heartbeat received",
                "VALUE": f"{item['fill_level']}%" if is_critical else f"{item['battery']}% battery",
                "SEVERITY": "Critical" if is_critical else "Normal",
            }
        )

    with st.container(border=True, key="sensor_activity"):
        activity_title, activity_state = st.columns([1, 1], vertical_alignment="center")
        with activity_title:
            st.markdown('<div class="event-heading">Live Sensor Activity</div>', unsafe_allow_html=True)
            st.markdown('<div class="event-caption">IoT telemetry stream from ultrasonic, thermal and battery sensors</div>', unsafe_allow_html=True)
        with activity_state:
            st.markdown(
                f'<div style="text-align:right;color:#899597;font:10px \'IBM Plex Mono\',monospace">streaming · {len(event_rows)} events</div>',
                unsafe_allow_html=True,
            )
        st.dataframe(pd.DataFrame(event_rows), hide_index=True, width="stretch", height=210)

