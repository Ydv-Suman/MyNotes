from app.utils.filename import sanitize_title
from app.utils.files import ordered_image_name, validate_image_batch
from app.services.pdf_service import pdf_formula_text, pdf_table_data


def demo() -> None:
    names = ["page-1.jpg"]
    validate_image_batch(names, ["image/jpeg"], 1, 100)
    assert ordered_image_name(1, "scan.jpeg", "image/jpeg") == "001.jpg"
    assert ordered_image_name(12, "scan.png", "image/png") == "012.png"
    assert sanitize_title(" Chapter 4: Devices? ") == "Chapter 4 Devices"
    assert pdf_formula_text("CPI = ∑_(i=1)^n (CPI_i * I_i) / I_c") == (
        "CPI = ∑<sub>i=1</sub><super>n</super> "
        "(CPI<sub>i</sub> × I<sub>i</sub>) ÷ I<sub>c</sub>"
    )
    assert pdf_formula_text(r"CPI = \sum_{i=1}^{n} \frac{CPI_i \times I_i}{I_c}") == (
        "CPI = ∑<sub>i=1</sub><super>n</super> "
        "(CPI<sub>i</sub> × I<sub>i</sub>) ÷ (I<sub>c</sub>)"
    )
    assert pdf_formula_text(r"T = \frac{I_c \times CPI}{Clock Rate f}") == (
        "T = (I<sub>c</sub> × CPI) ÷ (Clock Rate f)"
    )
    assert pdf_table_data({"headers": ["Name", "Score"], "rows": [["A", 10], ["B"]]}) == (
        ["Name", "Score"],
        [["A", "10"], ["B", ""]],
    )

    try:
        validate_image_batch([f"page-{i}.jpg" for i in range(101)], ["image/jpeg"] * 101, 1, 100)
    except ValueError as exc:
        assert "1-100" in str(exc)
    else:
        raise AssertionError("oversized batch was accepted")


if __name__ == "__main__":
    demo()
    print("phase1 selfcheck ok")
