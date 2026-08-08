"""Google Gemini, used by the Advisor Agent to write its shift briefing.

Simulated unless GEMINI_API_KEY is set - the same convention
core.services.twilio_verify and core.agents.manager_agent.send_sms already
follow, so local development, tests and CI never need a key. Without one,
_template_briefing() writes the same paragraph from the same figures, and
nothing else in the system behaves differently.

What the model is and is not allowed to do
------------------------------------------
It is handed figures the four other agents have already computed, and asked
for two or three sentences of prose. It decides no operations. Every fact
it can mention was established by a rule in an agent before this module was
called, and no output of this module is written back to a Booking, a
Platform or a Train - it only ever becomes one line in the audit trail.

That boundary is the whole design. A language model that could re-platform
a train or cancel a delay notice would be a far worse failure than an
awkward sentence, and grounding it in supplied numbers is what keeps a
plausible-sounding invention out of a station master's instructions.

Called through the REST endpoint with `requests`, which this project
already depends on, rather than adding the google-generativeai SDK for one
call.
"""

import os

import requests

# Overridable, because model names move faster than this project will.
DEFAULT_MODEL = "gemini-2.0-flash"

ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

# Low, because this is a briefing rather than a piece of writing - the same
# figures should produce much the same paragraph twice.
TEMPERATURE = 0.2
MAX_OUTPUT_TOKENS = 220

TIMEOUT_SECONDS = 12

INSTRUCTION = (
    "You are the advisory agent in a Bangladesh Railway control room. "
    "Write a two or three sentence shift briefing for the station master "
    "from the figures below. Use only these figures - do not invent trains, "
    "platforms, times or causes, and do not give instructions that are not "
    "already listed. Plain English, no bullet points, no greeting."
)


def _facts_block(facts):
    """The grounding block, in a fixed order so the prompt is reproducible."""
    lines = [
        f"Decisions recorded this shift: {facts['total_decisions']}",
        f"High-severity alerts standing: {facts['high_severity']}",
        f"Journeys currently delayed: {facts['delayed']}",
        f"Journeys flagged at risk: {facts['at_risk']}",
    ]
    if facts["by_agent"]:
        busiest = ", ".join(
            f"{agent} {count}" for agent, count in sorted(facts["by_agent"].items())
        )
        lines.append(f"Actions per agent: {busiest}")
    if facts["suggestions"]:
        lines.append("Standing recommendations:")
        lines.extend(f"- {s}" for s in facts["suggestions"])
    return "\n".join(lines)


def _template_briefing(facts):
    """The briefing written without a model. Deterministic, and always valid.

    Not a placeholder for the real thing so much as the floor beneath it:
    when the key is missing, the quota is spent or the call times out, the
    station master still gets a sentence, and the agent cycle still settles
    to the same state it would have reached anyway.
    """
    delayed = facts["delayed"]
    at_risk = facts["at_risk"]
    high = facts["high_severity"]

    if delayed or at_risk:
        opening = (
            f"{delayed} journey(s) running late and {at_risk} flagged at risk "
            f"after {facts['total_decisions']} agent decisions this shift."
        )
    else:
        opening = (
            f"No journey is late or at risk after {facts['total_decisions']} "
            "agent decisions this shift."
        )

    if high >= 2:
        pressure = (
            f" {high} high-severity alerts are standing, so station capacity "
            "is the binding constraint rather than train availability."
        )
    elif high:
        pressure = f" {high} high-severity alert is standing."
    else:
        pressure = ""

    if facts["suggestions"]:
        follow = f" {len(facts['suggestions'])} recommendation(s) are open below."
    else:
        follow = " Nothing needs a decision from you right now."

    return opening + pressure + follow


def write_briefing(facts):
    """Return (briefing_text, source) where source is 'gemini' or 'template'.

    Never raises. A briefing is a nice-to-have sitting at the end of the
    cycle; a control room losing its Scheduler because a text-generation
    API was slow would be an absurd trade, so every failure path here ends
    at the template.
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return _template_briefing(facts), "template"

    model = os.environ.get("GEMINI_MODEL", DEFAULT_MODEL)
    prompt = f"{INSTRUCTION}\n\n{_facts_block(facts)}"

    try:
        response = requests.post(
            ENDPOINT.format(model=model),
            params={"key": api_key},
            json={
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "temperature": TEMPERATURE,
                    "maxOutputTokens": MAX_OUTPUT_TOKENS,
                },
            },
            timeout=TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        payload = response.json()
        text = payload["candidates"][0]["content"]["parts"][0]["text"].strip()
    except (requests.RequestException, KeyError, IndexError, ValueError):
        # Includes a blocked or empty candidate, which arrives as a missing
        # key rather than an HTTP error.
        return _template_briefing(facts), "template"

    if not text:
        return _template_briefing(facts), "template"

    return text, "gemini"
