from importlib import resources

from screening_service.data_loader import load_sample_watchlist


def test_sample_watchlist_resource_is_packaged() -> None:
    resource = (
        resources.files("screening_service")
        .joinpath("data/watchlist.sample.json")
    )

    assert resource.is_file()


def test_load_sample_watchlist_returns_expected_records() -> None:
    watchlist = load_sample_watchlist()

    assert len(watchlist) == 6
    assert watchlist[0]["watchlist_id"] == "wl-001"
    assert watchlist[0]["primary_name"] == "John A Smith"
    assert watchlist[0]["aliases"] == ["John Smith"]
    assert watchlist[2]["countries"] == ["ES", "MX"]
    assert watchlist[5]["birth_year"] == 1992


def test_sample_watchlist_covers_planned_example_types() -> None:
    watchlist = load_sample_watchlist()

    assert any(entry["primary_name"] == "John A Smith" for entry in watchlist)
    assert any("Ali Khan" in entry["aliases"] for entry in watchlist)
    assert any(entry["primary_name"] == "Jon Smyth" for entry in watchlist)
    assert any(entry["countries"] for entry in watchlist)
    assert any(entry["birth_year"] is None for entry in watchlist)
