import sys

from PyQt5.QtWidgets import QApplication

from ui.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    app.setFont(__import__('PyQt5.QtGui', fromlist=['QFont']).QFont('Malgun Gothic', 10))

    window = MainWindow()
    window.show()

    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
