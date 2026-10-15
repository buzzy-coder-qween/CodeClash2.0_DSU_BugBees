"""
core/genai.py - Generative AI integration for EcoTwin using Google GenAI SDK.
Connects the digital twin telemetry to Google Gemini (gemini-2.5-flash / gemini-2.0-flash)
for:
  1. AI-Driven Route Optimization & Dispatch Explanation
  2. Waste Segregation & Environmental Impact Guidance
  3. Digital Twin AI Copilot (Natural-language operational Q&A)
"""

import os
from datetime import datetime
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv

# Ensure environment variables are loaded
load_dotenv(override=True)


def get_api_key() -> Optional[str]:
    """Retrieves the Gemini API key from environment or Streamlit session state if available."""
    load_dotenv(override=True)
    key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not key:
        try:
            import streamlit as st
            # Avoid accessing session_state if not running inside a Streamlit script context
            if hasattr(st, "runtime") and st.runtime.exists():
                key = st.session_state.get("gemini_api_key")
        except Exception:
            pass
    return key.strip() if key else None


def is_genai_available() -> bool:
    """Returns True if a valid API key is configured."""
    return bool(get_api_key())


def get_genai_client():
    """Initializes and returns the official Google GenAI client, or None if no key configured."""
    api_key = get_api_key()
    if not api_key:
        return None
    try:
        from google import genai
        return genai.Client(api_key=api_key)
    except Exception as e:
        print(f"[EcoTwin GenAI] Client init error: {e}")
        return None


def generate_ai_route_plan(
    bins: List[Dict[str, Any]],
    vehicles: Optional[Dict[str, Any]] = None,
    preferred_model: str = "gemini-2.5-flash",
) -> str:
    """
    Sends the current digital twin bin states to Gemini to generate
    an explainable, prioritized collection route with dispatch rationale.
    """
    client = get_genai_client()

    # Build concise telemetry context
    bin_summaries = []
    for b in bins:
        bid = b.get("Bin ID", "Unknown")
        fill = b.get("fill_level", 0)
        temp = b.get("temperature", 22.0)
        batt = b.get("battery", 100)
        btype = b.get("type", "General")
        status = "CRITICAL" if fill >= 85 else "WARNING" if fill >= 70 else "NORMAL"
        bin_summaries.append(
            f"- {bid} | Type: {btype} | Fill: {fill}% [{status}] | Temp: {temp:.1f}°C | Battery: {batt}%"
        )
    bins_text = "\n".join(bin_summaries)

    vehicles_text = ""
    if vehicles:
        v_lines = [f"- {vid}: {v['name']} (Cap: {v['capacity_liters']}L, Status: {v['status']})" for vid, v in vehicles.items()]
        vehicles_text = "\nAVAILABLE VEHICLES:\n" + "\n".join(v_lines)

    # Offline simulation fallback if no API key is configured
    if not client:
        critical_bins = [b for b in bins if b.get("fill_level", 0) >= 85]
        warning_bins = [b for b in bins if 70 <= b.get("fill_level", 0) < 85]
        normal_bins = [b for b in bins if b.get("fill_level", 0) < 70]
        ordered = critical_bins + warning_bins + normal_bins

        route_preview = [
            "⚡ **[Simulation Mode - Add GEMINI_API_KEY in .env for live Gemini intelligence]**\n",
            "### 🚚 Optimized Collection Route Plan",
            "**Strategy**: Dynamic priority dispatch based on overflow probability and telemetry risk.",
            "",
            "#### Recommended Sequence:",
        ]
        for i, b in enumerate(ordered, 1):
            bid = b.get("Bin ID", "").split(" (")[0]
            loc = b.get("Bin ID", "").split(" (")[-1].rstrip(")")
            fill = b.get("fill_level", 0)
            status = "🚨 Critical" if fill >= 85 else "⚠️ Warning" if fill >= 70 else "✅ Routine"
            reason = (
                "Spillover imminent, requires high-capacity vehicle"
                if fill >= 85
                else "Approaching threshold within next 3 hours"
                if fill >= 70
                else "Routine pickup on return leg"
            )
            route_preview.append(f"{i}. **{bid}** ({loc}) — `{fill}% full` · {status}\n   *Rationale: {reason}*")

        route_preview.extend([
            "",
            "#### 🌿 Fleet & Carbon Efficiency:",
            "- **Clustering**: Grouping campus district stops reduces total transit distance by estimated 18%.",
            "- **Truck Allocation**: Dispatch TRUCK-01 for immediate clearance of critical points.",
        ])
        return "\n".join(route_preview)

    # Prompt for Gemini
    prompt = f"""
You are the EcoTwin AI Dispatcher for a smart campus/metro municipal waste network.
Analyze the following digital twin sensor telemetry and formulate an optimal, explainable collection route.

CURRENT TELEMETRY DATA:
{bins_text}
{vehicles_text}

INSTRUCTIONS:
1. Formulate a prioritized collection sequence (Stop 1, Stop 2, etc.).
2. For each stop, provide a clear, actionable rationale (mention fill level, overflow hazard, temperature/spoilage risk, or battery maintenance).
3. Provide a brief "Fleet & Eco Efficiency" insight explaining how the routing saves fuel or reduces CO2 emissions.
4. Keep the output clean, professional, and formatted in markdown.
"""

    models_to_try = [preferred_model, "gemini-2.0-flash", "gemini-1.5-flash"]
    last_error = None
    for model_name in models_to_try:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
            )
            if response and response.text:
                return response.text.strip()
        except Exception as e:
            last_error = e
            continue

    return f"⚠️ Error contacting Gemini API ({last_error}). Check your GEMINI_API_KEY in .env."


def get_waste_disposal_advice(
    item_name: str,
    category: str,
    risk: Optional[str] = "Low",
    preferred_model: str = "gemini-2.5-flash",
) -> Dict[str, str]:
    """
    Generates tailored disposal advice, environmental impact estimates,
    and handling precautions for a segregated or deposited waste item.
    """
    client = get_genai_client()

    # Rule-based fallback if offline
    fallback_data = {
        "Plastics": {
            "advice": "Rinse out liquids, remove bottle caps if different plastic, and compress to save bin space.",
            "impact": "Takes 450+ years to decompose. Recycling 1 ton of plastic saves ~1,000–2,000 gallons of petroleum.",
            "eco_tip": "Look for PET (1) or HDPE (2) resin codes for high-grade circular recyclability.",
        },
        "Recyclable": {
            "advice": "Ensure item is clean and dry. Keep free of grease or food residues.",
            "impact": "Recycling metals and paper saves up to 70% energy compared to raw material extraction.",
            "eco_tip": "Keep dry recyclables separated from wet kitchen waste to prevent cross-contamination.",
        },
        "Compost": {
            "advice": "Ideal for organic aerobic digestion. Exclude stickers, plastic wrappers, or treated wood.",
            "impact": "Composting diverts methane emissions from landfills and yields organic bio-fertilizer.",
            "eco_tip": "Balance 'greens' (nitrogen-rich food) with 'browns' (carbon-rich paper/leaves).",
        },
        "Hazardous": {
            "advice": "DO NOT crush, puncture, or expose to heat. Tape battery terminals before placing in collection.",
            "impact": "Prevents heavy metals (lead, cadmium, mercury) from leaching into groundwater.",
            "eco_tip": "Schedule pickup with specialized certified e-waste recyclers.",
        },
        "Landfill": {
            "advice": "Dispose in general waste bin. Review packaging for multi-layer unrecyclable laminates.",
            "impact": "Decomposes anaerobically in landfills, releasing greenhouse gases over decades.",
            "eco_tip": "Consider choosing reusable or plastic-free alternatives for future purchases.",
        },
    }

    # Normalize category for fallback lookup
    matched_cat = "Landfill"
    for key in fallback_data:
        if key.lower() in category.lower() or category.lower() in key.lower():
            matched_cat = key
            break

    default_result = fallback_data.get(matched_cat, fallback_data["Landfill"])

    if not client:
        return default_result

    prompt = f"""
A smart waste station just identified a waste item:
- Item: {item_name}
- Stream/Category: {category}
- Risk Level: {risk or 'Standard'}

Provide 3 quick, structured insights strictly in this format:
ADVICE: <1 concise practical sorting/preparation tip under 20 words>
IMPACT: <1 fact on decomposition time, CO2 saving, or landfill diversion under 20 words>
ECO_TIP: <1 actionable circular economy or reduction tip under 20 words>
"""

    models_to_try = [preferred_model, "gemini-2.0-flash", "gemini-1.5-flash"]
    for model_name in models_to_try:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
            )
            text = response.text.strip()
            advice, impact, eco_tip = default_result["advice"], default_result["impact"], default_result["eco_tip"]
            for line in text.split("\n"):
                line = line.strip()
                if line.startswith("ADVICE:"):
                    advice = line.replace("ADVICE:", "").strip()
                elif line.startswith("IMPACT:"):
                    impact = line.replace("IMPACT:", "").strip()
                elif line.startswith("ECO_TIP:"):
                    eco_tip = line.replace("ECO_TIP:", "").strip()
            return {"advice": advice, "impact": impact, "eco_tip": eco_tip}
        except Exception:
            continue

    return default_result


def ask_digital_twin_copilot(
    query: str,
    bins: List[Dict[str, Any]],
    conversation_history: Optional[List[Dict[str, str]]] = None,
    preferred_model: str = "gemini-2.5-flash",
) -> str:
    """
    Answers natural-language operator questions regarding the digital twin network,
    sensor anomalies, and municipal waste logistics.
    """
    client = get_genai_client()

    # Telemetry summary
    bin_summaries = []
    for b in bins:
        bid = b.get("Bin ID", "Unknown")
        fill = b.get("fill_level", 0)
        temp = b.get("temperature", 22.0)
        batt = b.get("battery", 100)
        btype = b.get("type", "General")
        bin_summaries.append(f"{bid}: Fill={fill}%, Temp={temp:.1f}°C, Batt={batt}%, Type={btype}")
    telemetry_ctx = "; ".join(bin_summaries)

    if not client:
        return (
            "⚡ **[Simulation Mode]** Gemini API key not found. "
            "Please configure `GEMINI_API_KEY` in your `.env` or Settings tab to chat with the live EcoTwin Copilot.\n\n"
            f"**Current State Snapshot:** Monitoring {len(bins)} bins. "
            f"Average fill is {round(sum(b.get('fill_level', 0) for b in bins) / max(1, len(bins)))}%."
        )

    system_instruction = f"""
You are the EcoTwin AI Assistant, an expert digital twin co-pilot for municipal and campus waste management.
You have direct visibility into the IoT sensors of the smart bin network:
LIVE NETWORK STATUS:
{telemetry_ctx}

Answer operator queries accurately, concisely, and helpfully.
If an operator asks about overflow risks, high temperatures (potential fire/spoilage), or battery depletion, pinpoint the specific bin IDs and recommend solutions.
Keep responses conversational, professional, and easy to read.
"""

    prompt = f"{system_instruction}\n\nOPERATOR QUERY: {query}\n\nECOTWIN COPILOT RESPONSE:"

    models_to_try = [preferred_model, "gemini-2.0-flash", "gemini-1.5-flash"]
    last_error = None
    for model_name in models_to_try:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
            )
            if response and response.text:
                return response.text.strip()
        except Exception as e:
            last_error = e
            continue

    return f"⚠️ Copilot error: {last_error}"
