'''Helpers'''
import os
import mimetypes
import pdb
import typing as T

from PyQt5.QtWidgets import QLabel, QScrollBar
from PyQt5.QtCore import pyqtRemoveInputHook


def listImageFiles(directory: str) -> T.Generator[str, None, None]:
    '''Given a directory, yield all the images files in the tree.'''
    for root, _, files in os.walk(directory):
        for fname in files:
            typ, __ = mimetypes.guess_type(fname)
            if typ and typ.startswith('image/'):
                full_path = os.path.join(root, fname)
                yield os.path.relpath(full_path, directory)


def computeScrollBarAdjustment(scrollbar: QScrollBar, scale: float):
    '''Calculate the adjustment for the scroll bar at the scale factor.'''
    adj = scale * scrollbar.value() + ((scale - 1) * scrollbar.pageStep() / 2)
    return adj


def updateCountLabel(label: QLabel, message: str, count: int):
    '''Update a label that's showing a count of something.'''
    label.setText(message + ': ' + str(count))


def setPDBTrace():
    pyqtRemoveInputHook()
    pdb.set_trace()
