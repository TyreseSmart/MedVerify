"""
Core AI analysis module.
"""

import re
import torch
import streamlit as st
from threading import Thread
from transformers import (
    AutoProcessor,
    AutoModelForImageTextToText,
    TextIteratorStreamer,
)

MODEL_ID = "google/medgemma-1.5-4b-it"


@st.cache_resource(show_spinner="⏳ Loading MedGemma 1.5-4B (first run may take a few minutes)…")
def load_model():
    """
    Load MedGemma 1.5-4B-IT model and processor.
    """
    model = AutoModelForImageTextToText.from_pretrained(
        MODEL_ID,
        torch_dtype=torch.bfloat16,
        device_map="auto",
        attn_implementation="sdpa",   # SDPA attention acceleration
    )
    processor = AutoProcessor.from_pretrained(MODEL_ID)
    return model, processor


def build_messages(health_claim: str) -> list:
    """
    Build messages list for the model.
    """
    system_text = (
        "You are an expert medical fact-checker and practicing physician. "
        "Your task is to analyze health claims and identify medical misinformation. "
        "You must always respond in English. "
        "Use professional but accessible language for the general public."
    )

    user_text = f"""Perform a professional medical fact-check on the following health claim:

【Claim to verify】
{health_claim}

Respond in the following format (keep each bracketed tag):

[Credibility Score] An integer 0-100 (0=completely false, 100=fully credible)

[Risk Level] Exactly one of: Safe, Misleading, Dangerous

[Risk Reason] 1-2 sentences explaining why this risk level was assigned

[Medical Accuracy] Assess the claim's accuracy from a medical science perspective (2-4 sentences)

[Logical Fallacies] List any logical errors in the claim (each item starting with "-", or "None" if none)

[Evidence Summary] How current medical evidence supports or contradicts the claim (2-3 sentences)

[Key Misconceptions] The most important misconceptions in the claim (each item starting with "-", or "None" if none)

[Scientific Rebuttal] A science-based rebuttal suitable for social media (100-150 words, clear language)

[Expert Recommendation] Practical health advice for the general user (1-2 sentences)"""

    return [
        {
            "role": "system",
            "content": [{"type": "text", "text": system_text}]
        },
        {
            "role": "user",
            "content": [{"type": "text", "text": user_text}]
        }
    ]


# Parser utility functions

def extract_section(text: str, tag: str) -> str:
    """Extract content between [tag] and the next [...]."""
    pattern = rf'\[{re.escape(tag)}\]\s*(.*?)(?=\[[^\]]+\]|$)'
    match = re.search(pattern, text, re.DOTALL)
    return match.group(1).strip() if match else ""


def extract_list_items(section_text: str) -> list:
    """Extract list items starting with - • *."""
    items = []
    for line in section_text.splitlines():
        line = line.strip()
        if line.startswith(('-', '•', '·', '*')):
            cleaned = line.lstrip('-•·* ').strip()
            if cleaned and cleaned.lower() not in ("none", "n/a", "na"):
                items.append(cleaned)
    if not items and section_text.strip() and section_text.strip().lower() not in ("none", "n/a", "na"):
        items.append(section_text.strip())
    return items


def extract_score(score_text: str) -> int:
    """Extract 0-100 integer score from text."""
    for token in re.findall(r'\d+', score_text):
        val = int(token)
        if 0 <= val <= 100:
            return val
    return 50


def parse_model_output(raw_text: str) -> dict:
    """
    Parse model natural language output into a structured result dict.
    Called by app.py after streaming finishes to parse the full text.
    """
    if not raw_text or not raw_text.strip():
        return {
            "credibility_score":  0,
            "risk_level":         "Misleading",
            "risk_reason":        "Model produced no output; check HF token and GPU memory.",
            "medical_accuracy":   "Analysis failed; please try again.",
            "logical_fallacies":  [],
            "evidence_summary":   "Please verify against medical literature manually.",
            "key_misconceptions": [],
            "rebuttal":           "This claim needs further verification; consult a healthcare professional.",
            "recommendation":     "For health-related information, consult a qualified healthcare provider.",
            "_parse_error":       True,
            "_raw_output":        "(empty)",
        }

    score_text      = extract_section(raw_text, "Credibility Score")
    risk_level_text = extract_section(raw_text, "Risk Level")
    risk_reason     = extract_section(raw_text, "Risk Reason")
    medical_acc     = extract_section(raw_text, "Medical Accuracy")
    fallacies_text  = extract_section(raw_text, "Logical Fallacies")
    evidence        = extract_section(raw_text, "Evidence Summary")
    misconceptions  = extract_section(raw_text, "Key Misconceptions")
    rebuttal        = extract_section(raw_text, "Scientific Rebuttal")
    recommendation  = extract_section(raw_text, "Expert Recommendation")

    risk_level = "Misleading"
    for level in ["Safe", "Misleading", "Dangerous"]:
        if level.lower() in risk_level_text.lower():
            risk_level = level
            break

    return {
        "credibility_score":  extract_score(score_text),
        "risk_level":         risk_level,
        "risk_reason":        risk_reason  or "Not provided",
        "medical_accuracy":   medical_acc  or raw_text[:500],
        "logical_fallacies":  extract_list_items(fallacies_text),
        "evidence_summary":   evidence     or "No evidence description found",
        "key_misconceptions": extract_list_items(misconceptions),
        "rebuttal":           rebuttal     or "Consult a healthcare professional for more information.",
        "recommendation":     recommendation or "For health-related information, consult a qualified healthcare provider.",
        "_raw_output":        raw_text,
    }


def analyze_health_claim_stream(health_claim: str):
    """
    Stream model output for health claim analysis.
    """
    if not health_claim or not health_claim.strip():
        raise ValueError("Health claim cannot be empty")

    # Step 1: Load model
    model, processor = load_model()

    # Step 2: Build messages
    messages = build_messages(health_claim.strip())

    # Step 3: apply_chat_template
    inputs = processor.apply_chat_template(
        messages,
        add_generation_prompt=True,
        tokenize=True,
        return_dict=True,
        return_tensors="pt"
    ).to(model.device, dtype=torch.bfloat16)

    # Step 4: Create streamer
    streamer = TextIteratorStreamer(
        processor.tokenizer,
        skip_prompt=True,        # Do not repeat the input prompt in output
        skip_special_tokens=True,        # Filter special tokens like <eos>
    )

    # Step 5: Run model.generate in background thread
    generation_kwargs = dict(
        **inputs,
        streamer=streamer,
        max_new_tokens=800,   
        do_sample=False,       # Greedy decoding for stable output
    )
    thread = Thread(target=model.generate, kwargs=generation_kwargs)
    thread.start()

    # Step 6: Yield tokens to app.py (streaming core)
    # app.py consumes this generator with st.write_stream() for real-time display
    for token_text in streamer:
        yield token_text

    # Step 7: Wait for generation thread to finish (ensure resource cleanup)
    thread.join()
