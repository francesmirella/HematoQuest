import os
print("STEP 1: imports starting")

import streamlit as st
print("STEP 2: streamlit imported")

from src.db import get_recent, get_stats, init_db, save_attempt
print("STEP 3: db imported")

from src.question_engine import generate_question, load_blocks
print("STEP 4: question_engine imported")

from src.reference_engine import (
    auto_ingest_local_references,
    build_explanation_context,
    build_style_context,
    get_default_reference_files,
    get_reference_labels,
    ingest_pdf_file,
)
print("STEP 5: reference_engine imported")

st.set_page_config(page_title="HematoQuest Debug", page_icon="🩸", layout="wide")
print("STEP 6: page config set")

init_db()
print("STEP 7: db initialized")

blocks = load_blocks()
print(f"STEP 8: blocks loaded ({len(blocks)} items)")

temas = ["Todos"] + sorted({item["tema"] for item in blocks})
print(f"STEP 9: temas created ({len(temas)} items)")

auto_ingest_local_references()
print("STEP 10: auto_ingest done")

st.title("🩸 HematoQuest (Debug)")
st.write("Se você está vendo isso, o app carregou!")

# Simplified initialization
if "question" not in st.session_state:
    st.session_state.question = None
    
style_files, explanation_files = get_default_reference_files()
print(f"STEP 11: default files (s={len(style_files)}, e={len(explanation_files)})")

tema = st.selectbox("Tema", temas, key="tema_main")
print("STEP 12: selectbox created")

if st.button("Gerar questão"):
    print("STEP 13: button clicked, generating...")
    q = generate_question(tema)
    st.session_state.question = q
    print("STEP 14: question generated")
    st.rerun()

print("STEP 15: checking question state")
if st.session_state.question:
    q = st.session_state.question
    st.subheader("Questão")
    st.write(q.pergunta)
    st.radio("Resposta", q.alternativas, key="resp")
    print("STEP 16: question displayed")
else:
    st.info("Clique em 'Gerar questão' para começar")
    print("STEP 16b: no question yet")

print("STEP FINAL: app finished rendering")
