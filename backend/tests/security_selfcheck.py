from pathlib import Path
from tempfile import TemporaryDirectory

from PIL import Image

from app.config import database_url
from app.services.pdf_service import pdf_text
from app.utils.files import validate_image_content


def demo() -> None:
    assert pdf_text("<b>unsafe</b> & text") == "&lt;b&gt;unsafe&lt;/b&gt; &amp; text"
    assert database_url().startswith(("sqlite:", "postgresql+psycopg:"))

    with TemporaryDirectory() as directory:
        fake = Path(directory) / "fake.jpg"
        fake.write_bytes(b"not an image")
        try:
            validate_image_content(fake)
        except ValueError:
            pass
        else:
            raise AssertionError("Spoofed image was accepted")

        real = Path(directory) / "real.jpg"
        Image.new("RGB", (1, 1)).save(real, format="JPEG")
        validate_image_content(real)


if __name__ == "__main__":
    demo()
    print("security selfcheck ok")
