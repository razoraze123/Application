from PySide6.QtCore import QEasingCurve, QPropertyAnimation
from PySide6.QtWidgets import QProgressBar


class AnimatedProgressBar(QProgressBar):
    """Progress bar with smooth value animation and gradient coloring."""

    def __init__(self) -> None:
        super().__init__()
        self.setRange(0, 100)
        self.setValue(0)
        self.setFormat("%p%")
        self.setTextVisible(True)

        self._anim = QPropertyAnimation(self, b"value")
        self._anim.setDuration(300)
        self._anim.setEasingCurve(QEasingCurve.InOutCubic)

        self.setStyleSheet(
            """
            QProgressBar {
                background-color: #3c3c3c;
                border: 1px solid #555;
                border-radius: 6px;
                text-align: center;
                height: 20px;
            }
            QProgressBar::chunk {
                border-radius: 6px;
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 #0078d7, stop:1 #00c2ff
                );
            }
            """
        )

    def set_animated_value(self, value: int) -> None:
        """Animate progress bar value change."""
        self._anim.stop()
        self._anim.setStartValue(self.value())
        self._anim.setEndValue(value)
        self._anim.start()
