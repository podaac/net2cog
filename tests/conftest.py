import pytest

def pytest_addoption(parser):
    parser.addoption(
        "--cid", action="store", default="C2842849693-LARC_CLOUD", help="Concept ID for downloading granule"
    )

@pytest.fixture(scope="session")
def concept_id(request):
    return request.config.getoption("--cid")
