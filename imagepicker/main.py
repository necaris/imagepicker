#!/usr/bin/env python
#-*- coding: utf-8 -*-
'''
Image viewer and chooser application -- load up a set of images, read from a
file or a directory subtree, and work through them.

Modified from the PyQt5 imageviewer example application
'''
import sys
import typing as T

from PyQt5.QtWidgets import QApplication

from imagepicker.ui import ImagePicker


def main(argv: T.List[str]=None) -> None:
    '''Get the application started.'''
    if not argv:
        argv = sys.argv

    app = QApplication(argv)
    picker = ImagePicker()
    picker.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main(sys.argv)
