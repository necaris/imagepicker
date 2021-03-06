#!/usr/bin/env python
#-*- coding: utf-8 -*-
'''
Image viewer and chooser application -- load up a set of images, read from a
file or a directory subtree, and work through them.

Modified from the PyQt5 imageviewer example application
'''
import sys
import logging
import typing as T

from PyQt5.QtWidgets import QApplication

from imagepicker import __version__
from imagepicker.ui import ImagePicker


def main(argv: T.List[str]=None) -> None:
    '''Get the application started.'''
    if not argv:
        argv = sys.argv

    if len(argv) > 1 and argv[1] == '-V':
        print(__version__)
        sys.exit(0)

    logging.basicConfig(format='%(asctime)s %(levelname)s %(module)s %(funcName)s: %(message)s')
    logger = logging.getLogger(__name__)
    # logger.setLevel(logging.DEBUG)

    app = QApplication(argv)
    picker = ImagePicker(logger=logger)
    app.installEventFilter(picker)
    picker.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main(sys.argv)
