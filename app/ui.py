import mimetypes
import sys
import time
from pathlib import Path

import streamlit as st

sys.path.append(str(Path(__file__).resolve().parent.parent))  # lets `streamlit run app/ui.py` import core

from core.extractor import extract_document
from core.loaders import load_document
from core.models import UnsupportedInputError, ValidationReport
from core.profiles import load_profiles
from core.providers import get_provider
from core.renderer import render_markdown

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
        pages = load_document(upload.getvalue(), mime)
        provider = get_provider()
        bar = st.progress(0.0, text="Starting...")
        started = time.perf_counter()
        results = extract_document(
            pages, provider, instruction,
            on_progress=lambda done, total: bar.progress(done / total, text=f"Page {done}/{total}"),
        )
        bar.empty()
        run_info = {
            "provider": provider.name,
            "model": provider.model,
            "total time": f"{time.perf_counter() - started:.1f}s",
            "tokens (in/out)": f"{sum(r.input_tokens or 0 for r in results)} / {sum(r.output_tokens or 0 for r in results)}",
            "cache hits": sum(r.cached for r in results),
            "failed pages": [r.page for r in results if r.error] or "none",
        }
        st.session_state["output"] = {
            "results": results, "run_info": run_info, "report": ValidationReport(),
            "markdown": render_markdown(results, None, run_info),
            "name": Path(upload.name).stem,
        }
    except (UnsupportedInputError, ValueError) as e:
        st.error(str(e))

out = st.session_state.get("output")
if not out:
    st.info("Upload a PDF or image, choose a profile, then press Run.")
else:
    failed = out["run_info"]["failed pages"]
    if failed != "none":
        st.error(f"{len(failed)} page(s) failed: {failed}. The other pages are shown below.")
    st.download_button("Download .md", out["markdown"], file_name=f"{out['name']}.md", mime="text/markdown")
    tab_result, tab_sources, tab_issues, tab_info = st.tabs(["Result", "Sources", "Issues", "Run info"])
    with tab_result:
        st.markdown(out["markdown"])
    with tab_sources:
        rows = [{"page": b.page, "key": b.key, "region": b.region, "status": b.status, "excerpt": b.excerpt}
                for r in out["results"] for b in r.blocks]
        st.dataframe(rows, width="stretch")
    with tab_issues:
        issues = out["report"].issues
        st.write([i.model_dump() for i in issues] if issues else "No validation yet (added in block 4).")
    with tab_info:
        st.json(out["run_info"])
