from sysbar.services.audio.models import SinkInput, group_sink_inputs, stable_app_id


def test_stable_id_prefers_app_id() -> None:
    si = SinkInput(index=1, app_id="org.app", binary="/usr/bin/app", name="App")
    assert stable_app_id(si) == "org.app"


def test_stable_id_falls_back_to_binary() -> None:
    si = SinkInput(index=1, app_id=None, binary="/usr/bin/app", name="App")
    assert stable_app_id(si) == "/usr/bin/app"


def test_stable_id_falls_back_to_index() -> None:
    assert stable_app_id(SinkInput(index=7)) == "sink-input-7"


def test_group_merges_streams_of_same_app() -> None:
    streams = [
        SinkInput(index=1, app_id="org.app", name="App", volume=0.5, corked=False),
        SinkInput(index=2, app_id="org.app", name="App", volume=0.9, corked=True),
    ]
    apps = group_sink_inputs(streams)
    assert len(apps) == 1
    assert apps[0].sink_input_indices == [1, 2]
    assert apps[0].volume == 0.5  # representative = first stream


def test_group_is_playing_when_any_stream_uncorked() -> None:
    streams = [
        SinkInput(index=1, app_id="a", corked=True),
        SinkInput(index=2, app_id="a", corked=False),
    ]
    assert group_sink_inputs(streams)[0].is_playing is True


def test_group_not_playing_when_all_corked() -> None:
    streams = [SinkInput(index=1, app_id="a", corked=True)]
    assert group_sink_inputs(streams)[0].is_playing is False


def test_group_muted_only_when_all_muted() -> None:
    streams = [
        SinkInput(index=1, app_id="a", muted=True),
        SinkInput(index=2, app_id="a", muted=False),
    ]
    assert group_sink_inputs(streams)[0].muted is False


def test_group_preserves_first_appearance_order() -> None:
    streams = [
        SinkInput(index=1, app_id="b", name="B"),
        SinkInput(index=2, app_id="a", name="A"),
        SinkInput(index=3, app_id="b", name="B"),
    ]
    assert [app.id for app in group_sink_inputs(streams)] == ["b", "a"]


def test_group_empty_returns_empty() -> None:
    assert group_sink_inputs([]) == []
