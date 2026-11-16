from __future__ import annotations

import os
import sys
from pathlib import Path


def main() -> int:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root))

    from PySide6.QtGui import QGuiApplication

    from galardo import icons

    app = QGuiApplication(sys.argv)  # noqa: F841 — needed for the font engine
    target = root / "assets" / "galardo.ico"
    icons.write_ico(target)
    print(f"Icon written: {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
