import mimetypes
import sys
from pathlib import Path

import streamlit as st

sys.path.append(str(Path(__file__).resolve().parent.parent))  # lets `streamlit run app/ui.py` import core

from core.models import UnsupportedInputError
from core.pipeline import run_pipeline, save_outputs
from core.profiles import load_profiles
from core.providers import get_provider

st.set_page_config(page_title="Document Extraction", layout="wide")
st.title("Document Extraction")

profiles = load_profiles()

with st.sidebar:
    upload = st.file_uploader("Document", type=["pdf", "png", "jpg", "jpeg"])
    profile_id = st.selectbox("Profile", list(profiles), format_func=lambda i: profiles[i].name)
    # keyed by profile so picking another profile replaces the text, while manual edits survive reruns
    instruction = st.text_area("Extraction instruction (editable)", profiles[profile_id].instruction,
                               height=220, key=f"instruction_{profile_id}")
    run = st.button("Run extraction", type="primary", disabled=upload is None)

if run and upload:
    # Streamlit reruns this script on every click, so results go into session_state
    st.session_state.pop("output", None)
    try:
        mime = upload.type or mimetypes.guess_type(upload.name)[0] or ""
        bar = st.progress(0.0, text="Starting...")
        result = run_pipeline(
            upload.getvalue(), mime, instruction, get_provider(),
            on_progress=lambda done, total: bar.progress(done / total, text=f"Page {done}/{total}"),
        )
        bar.empty()
        name = f"{Path(upload.name).stem}__{profile_id}"
        save_outputs(result, name)
        st.session_state["output"] = {"result": result, "name": name}
    except (UnsupportedInputError, ValueError) as e:
        st.error(str(e))

out = st.session_state.get("output")
if not out:
    st.info("Upload a PDF or image, choose a profile, then press Run.")
else:
    result = out["result"]
    failed = result.run_info["failed pages"]
    if failed != "none":
        st.error(f"{len(failed)} page(s) failed: {failed}. The other pages are shown below.")
    st.download_button("Download .md", result.markdown, file_name=f"{out['name']}.md", mime="text/markdown")
    tab_result, tab_sources, tab_issues, tab_info = st.tabs(["Result", "Sources", "Issues", "Run info"])
    with tab_result:
        st.markdown(result.markdown)
    with tab_sources:
        rows = [{"page": b.page, "key": b.key, "region": b.region, "status": b.status, "excerpt": b.excerpt}
                for r in result.results for b in r.blocks]
        st.dataframe(rows, width="stretch")
    with tab_issues:
        issues = result.report.issues
        st.write([i.model_dump() for i in issues] if issues else "No validation yet (added in block 4).")
    with tab_info:
        st.json(result.run_info)
