import logging
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


class ListHandler(logging.Handler):
    """Collects extraction log lines and redraws them live in a placeholder at the bottom of the page."""

    def __init__(self, box):
        super().__init__()
        self.lines: list[str] = []
        self.box = box
        self.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s", "%H:%M:%S"))

    def emit(self, record):
        self.lines.append(self.format(record))
        if self.box is not None:
            self.box.code("\n".join(self.lines), language=None)


logging.basicConfig(level=logging.INFO)  # also prints to the container logs
extraction_log = logging.getLogger("extraction")
extraction_log.setLevel(logging.INFO)

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
    handler = ListHandler(None)
    st.session_state["log"] = handler.lines
    extraction_log.addHandler(handler)
    try:
        mime = upload.type or mimetypes.guess_type(upload.name)[0] or ""
        bar = st.progress(0.0, text="Starting...")
        live_log = st.empty()  # below the progress bar, i.e. at the bottom while the run is in progress
        handler.box = live_log
        result = run_pipeline(
            upload.getvalue(), mime, instruction, get_provider(), profiles[profile_id].checks,
            on_progress=lambda done, total: bar.progress(done / total, text=f"Page {done}/{total}"),
        )
        bar.empty()
        live_log.empty()
        name = f"{Path(upload.name).stem}__{profile_id}"
        save_outputs(result, name)
        st.session_state["output"] = {"result": result, "name": name}
    except (UnsupportedInputError, ValueError) as e:
        st.error(str(e))
    finally:
        extraction_log.removeHandler(handler)

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
        rep = result.report
        c1, c2, c3 = st.columns(3)
        c1.metric("Page coverage", f"{rep.coverage:.0%}")
        c2.metric("Grounded evidence", "n/a" if rep.grounded_rate is None else f"{rep.grounded_rate:.0%}")
        c3.metric("Arithmetic checks", rep.checks_passed or "n/a")
        if issues:
            st.dataframe([i.model_dump() for i in issues], width="stretch")
        else:
            st.success("No validation issues.")
    with tab_info:
        st.json(result.run_info)

if st.session_state.get("log"):
    with st.expander("Logs", expanded=out is None):
        st.code("\n".join(st.session_state["log"]), language=None)
