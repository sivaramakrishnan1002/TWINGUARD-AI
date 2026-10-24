from tools.validate_api_contracts import validate_all


def test_openapi_contracts_parse_and_have_required_operations():
    results = validate_all()
    assert len(results) == 2
    assert {result["title"] for result in results} == {
        "TwinGuard AI Service",
        "TwinGuard Backend API",
    }
    assert all(result["operations"] >= 6 for result in results)
