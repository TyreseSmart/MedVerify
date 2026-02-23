# 🩺 MedVerify — Medical Misinformation Detection

A medical misinformation detection platform powered by **Google MedGemma 1.5-4B**, helping users identify medical myths and misleading health claims on social media.

---

## 📁 Project structure

```
medverify/
├── app.py                 # Streamlit main UI
├── medgemma_analyzer.py   # MedGemma AI analysis core
├── pubmed_search.py       # PubMed literature search
├── requirements.txt       # Python dependencies
└── README.md              # This file
```

---

## 🚀 Quick start

### 1. Environment setup

```bash
# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate        # Linux/Mac
# venv\Scripts\activate.bat    # Windows

# Install dependencies
pip install -r requirements.txt
```

> **GPU users** (recommended, 5–10x faster):
> ```bash
> pip install torch --index-url https://download.pytorch.org/whl/cu121
> ```

### 2. MedGemma access

MedGemma is a gated model. You need to:
1. Log in at [Hugging Face](https://huggingface.co/)
2. Open [google/medgemma-1.5-4b-it](https://huggingface.co/google/medgemma-1.5-4b-it) and accept the terms
3. Configure your HF token locally:
   ```bash
   huggingface-cli login
   # Enter your HF Access Token
   ```

### 3. Run the app

```bash
streamlit run app.py
```

Your browser will open `http://localhost:8501`.

---

## Deploy to Hugging Face Spaces

1. Create a new Space at [Hugging Face Spaces](https://huggingface.co/spaces) and choose the **Streamlit** SDK
2. Upload all project files
3. In Space Settings → Secrets, add:
   - `HF_TOKEN`: your Hugging Face Access Token
4. Select **T4 GPU** (free tier) or better

---

## ⚙️ Features

| Feature | Description |
|--------|-------------|
| **Credibility score** | 0–100 score reflecting medical/scientific reliability of the claim |
| **Risk level** | Three levels: Safe / Misleading / Dangerous |
| **Logical fallacies** | Detects common pseudoscience reasoning patterns |
| **Evidence summary** | Summary of evidence based on medical consensus |
| **Rebuttal text** | Auto-generated science-based rebuttals for social sharing |
| **PubMed literature** | Search for related medical papers and evidence links |

---

## 🔧 Tech stack

- **AI model**: Google MedGemma 1.5-4B-IT (Hugging Face Transformers)
- **Frontend**: Streamlit
- **Literature**: NCBI E-utilities API
- **Runtime**: Python 3.10+

---

## ⚠️ Disclaimer

This system is for reference only and does not constitute medical advice. AI analysis may contain errors. For health concerns, consult a licensed physician or qualified healthcare provider.
