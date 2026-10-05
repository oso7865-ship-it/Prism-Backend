from app.domain.analysis import contracts, pipeline


def test_total_source_limit_is_three_mebibytes_and_per_file_limit_is_unchanged():
    assert contracts.MAX_TOTAL == 3 * 1024 * 1024
    assert contracts.MAX_FILE == 200 * 1024
    assert contracts.MAX_FILES == 100


def test_pipeline_uses_the_contract_limit_and_the_total_cap_is_reachable():
    assert pipeline.MAX_TOTAL is contracts.MAX_TOTAL
    assert contracts.MAX_TOTAL > contracts.MAX_FILE
    # 15 maximum-size files fit under the cap; the 16th would exceed it.
    assert 15 * contracts.MAX_FILE <= contracts.MAX_TOTAL < 16 * contracts.MAX_FILE
