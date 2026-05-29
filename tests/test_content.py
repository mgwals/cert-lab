from cert_lab.content import load_catalog


def test_catalog_loads_expected_certifications() -> None:
    catalog = load_catalog()

    slugs = {certification["slug"] for certification in catalog["certifications"]}

    assert slugs == {"github-foundations", "az-900", "pcep"}


def test_each_certification_has_ten_original_practice_questions() -> None:
    catalog = load_catalog()

    for certification in catalog["certifications"]:
        assert len(certification["questions"]) == 10
        assert all("official_url" in certification for certification in catalog["certifications"])
