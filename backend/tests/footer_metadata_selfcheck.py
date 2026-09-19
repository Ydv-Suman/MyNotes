from app.services.vision_service import is_footer_metadata, remove_footer_metadata


def demo() -> None:
    lines = [
        "Photosynthesis",
        "Plants convert light into chemical energy",
        "Instructor: Dr. Rivera",
        "September 19, 2026",
    ]
    assert remove_footer_metadata(lines) == lines[:2]
    assert is_footer_metadata("Professor - Ada Lovelace")
    assert is_footer_metadata("09/19/2026")
    assert remove_footer_metadata(["History", "The treaty was signed on September 19, 2026."]) == [
        "History",
        "The treaty was signed on September 19, 2026.",
    ]


if __name__ == "__main__":
    demo()
    print("footer metadata selfcheck ok")
