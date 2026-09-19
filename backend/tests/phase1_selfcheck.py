from app.utils.filename import sanitize_title
from app.utils.files import ordered_image_name, validate_image_batch


def demo() -> None:
    names = [f"page-{i}.jpg" for i in range(10)]
    validate_image_batch(names, ["image/jpeg"] * 10, 10, 50)
    assert ordered_image_name(1, "scan.jpeg", "image/jpeg") == "001.jpg"
    assert ordered_image_name(12, "scan.png", "image/png") == "012.png"
    assert sanitize_title(" Chapter 4: Devices? ") == "Chapter 4 Devices"

    try:
        validate_image_batch(["one.jpg"], ["image/jpeg"], 10, 50)
    except ValueError as exc:
        assert "10-50" in str(exc)
    else:
        raise AssertionError("short batch was accepted")


if __name__ == "__main__":
    demo()
    print("phase1 selfcheck ok")
