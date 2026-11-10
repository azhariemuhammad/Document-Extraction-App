from core.extractor import MAX_ATTEMPTS, extract_document
from core.models import PageUnit
from core.pipeline import run_pipeline, save_outputs
from core.providers.fake import FakeProvider
from tests.test_block1 import make_pdf

PAGE = PageUnit(page_no=3, image_png=b"png", text_layer=None, width=1, height=1)
no_sleep = lambda seconds: None


def run(provider, pages=(PAGE,), doc=b"doc", instruction="x", sleeps=None):
    sleep = sleeps.append if sleeps is not None else no_sleep
    return extract_document(doc, list(pages), provider, instruction, sleep=sleep)


def test_retryable_error_is_retried_with_growing_waits():
    sleeps = []
    [r] = run(FakeProvider(fail_times=2), sleeps=sleeps)
    assert r.error is None and r.attempts == 3
    assert sleeps == [2, 4]


def test_gives_up_after_max_attempts_and_reports_it():
    provider = FakeProvider(fail_times=99)
    [r] = run(provider)
    assert "429" in r.error and r.attempts == MAX_ATTEMPTS == provider.calls


def test_non_retryable_error_is_not_retried():
    provider = FakeProvider(fail_times=99, retryable=False)
    [r] = run(provider)
    assert r.error and provider.calls == 1


def test_bad_json_gets_one_repair_call():
    provider = FakeProvider(bad_json_times=1)
    [r] = run(provider)
    assert r.error is None and r.attempts == 2 and r.blocks


def test_still_bad_after_repair_is_a_visible_page_error():
    provider = FakeProvider(bad_json_times=5)
    [r] = run(provider)
    assert "repair" in r.error and provider.calls == 2


def test_page_number_comes_from_us_not_the_model():
    [r] = run(FakeProvider())
    assert {b.page for b in r.blocks} == {3}


def test_second_run_is_served_from_cache_without_calling_the_provider():
    first = FakeProvider()
    run(first)
    second = FakeProvider()
    [r] = run(second)
    assert r.cached and second.calls == 0 and r.blocks


def test_cache_key_changes_with_instruction_and_document():
    run(FakeProvider(), instruction="a")
    for kwargs in ({"instruction": "b"}, {"doc": b"other"}):
        provider = FakeProvider()
        run(provider, **kwargs)
        assert provider.calls == 1


def test_failures_are_not_cached():
    run(FakeProvider(fail_times=99, retryable=False))
    provider = FakeProvider()
    [r] = run(provider)
    assert not r.cached and r.error is None


def test_one_failed_page_does_not_stop_the_others():
    pages = [PAGE.model_copy(update={"page_no": n}) for n in (1, 2, 3)]
    results = run(FakeProvider(fail_times=1, retryable=False), pages=pages)
    assert [bool(r.error) for r in results] == [True, False, False]


def test_pipeline_saves_markdown_and_json_and_reports_run_info(tmp_path):
    pdf = make_pdf(2)  # one file, uploaded twice
    out = run_pipeline(pdf, "application/pdf", "x", FakeProvider())
    assert out.run_info["pages"] == 2 and out.run_info["cache hits"] == 0
    md = save_outputs(out, "demo")
    assert md.exists() and md.with_suffix(".json").exists()
    again = run_pipeline(pdf, "application/pdf", "x", FakeProvider())
    assert again.run_info["cache hits"] == 2 and again.run_info["provider calls"] == 0
