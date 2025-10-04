from pyqtgraph.Qt.QtWidgets import QApplication
from gui import MainWindow


def main():
    app = QApplication([])
    window = MainWindow()
    window.show()
    exit(app.exec())


if __name__ == "__main__":
    main()
