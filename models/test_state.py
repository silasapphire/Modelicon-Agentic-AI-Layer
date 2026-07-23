from models.state import merge_dict


def test_merge_dict_combines_both_sides():
    assert merge_dict({"thermal": {"a": 1}}, {"lighting": {"b": 2}}) == {
        "thermal": {"a": 1},
        "lighting": {"b": 2},
    }


def test_merge_dict_handles_none():
    assert merge_dict(None, {"a": 1}) == {"a": 1}
    assert merge_dict({"a": 1}, None) == {"a": 1}
    assert merge_dict(None, None) == {}


def test_merge_dict_right_overwrites_same_key():
    assert merge_dict({"a": 1}, {"a": 2}) == {"a": 2}
