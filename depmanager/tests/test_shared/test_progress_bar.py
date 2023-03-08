def test_progress_bar_initialized(progress_bar):
    assert progress_bar.progress_count == 0
    assert progress_bar.progress_total == 100
    assert not progress_bar.progress_complete


def test_progress_bar_increments(progress_bar):
    assert progress_bar.progress_count == 0
    assert progress_bar.filled_len == 0
    assert progress_bar.percents == 0.0
    assert progress_bar.bar_fill == "-" * 60
    progress_bar.inc()
    assert progress_bar.progress_count == 1
    assert progress_bar.filled_len == 1
    assert progress_bar.percents == 1.0
    assert progress_bar.bar_fill == "=" + "-" * 59


def test_progress_bar_completes(progress_bar):
    assert progress_bar.progress_count == 0
    assert not progress_bar.progress_complete
    assert progress_bar.filled_len == 0
    assert progress_bar.percents == 0.0
    assert progress_bar.bar_fill == "-" * 60
    progress_bar.progress_count = 99

    progress_bar.inc()
    assert progress_bar.progress_count == 100
    assert progress_bar.progress_complete
    assert progress_bar.filled_len == 60
    assert progress_bar.percents == 100.0
    assert progress_bar.bar_fill == "=" * 60

    progress_bar.inc()
    assert progress_bar.progress_count == 100
    assert progress_bar.progress_complete
    assert progress_bar.filled_len == 60
    assert progress_bar.percents == 100.0
    assert progress_bar.bar_fill == "=" * 60
