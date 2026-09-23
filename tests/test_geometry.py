import pytest

from cbba.geometry import euclidean_distance


def test_distance_uses_z():
    # (0,0,0) -> (1,2,2): sqrt(1 + 4 + 4) = 3
    assert euclidean_distance((0, 0, 0), (1, 2, 2)) == 3


def test_distance_2d_still_works():
    # the existing tests use 2D positions; they must keep working
    assert euclidean_distance((0, 0), (3, 4)) == 5


def test_distance_rejects_mixed_dimensions():
    # a 2D agent and a 3D task is a bug somewhere upstream: fail loudly
    # instead of silently ignoring z
    with pytest.raises(ValueError):
        euclidean_distance((0, 0), (1, 2, 2))
