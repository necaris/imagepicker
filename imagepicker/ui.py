#-*- coding: utf-8 -*-
'''
Define the UI
'''
from functools import partial
import typing as T

from PyQt5.QtCore import Qt, QDir, QSize, pyqtSignal
from PyQt5.QtGui import QImage, QPalette, QPixmap, QIcon
from PyQt5.QtWidgets import (QAction, QFileDialog, QLabel,
                             QMainWindow, QMenu, QMessageBox, QScrollArea,
                             QSizePolicy, QHBoxLayout, QVBoxLayout,
                             QPushButton, QWidget)

from imagepicker.model import PickerModel
from imagepicker.utils import (computeScrollBarAdjustment, updateCountLabel)
# side-effect-ful import initializes the image resources we know about
import imagepicker.resources


ICON_HEART = QIcon(':/images/heart.svg')
ICON_DELETE = QIcon(':/images/delete.svg')


Actions = T.NamedTuple('Actions',
                       [('open', QAction), ('save', QAction), ('exit', QAction),
                        ('about', QAction), ('scaleToFullSize', QAction),
                        ('fitToWindow', QAction)])


Buttons = T.NamedTuple('Buttons',
                       [('previous', QPushButton), ('pick', QPushButton),
                        ('next', QPushButton)])


Labels = T.NamedTuple('Labels',
                      [('mainImage', QLabel), ('prevStripImage', QLabel),
                       ('currStripImage', QLabel), ('nextStripImage', QLabel),
                       ('total', QLabel), ('picked', QLabel),
                       ('input', QLabel), ('output', QLabel)])


class ResizeEmittingScrollArea(QScrollArea):
    '''QScrollArea that informs us on resize, so we can take action.'''
    resized = pyqtSignal(QSize)

    def resizeEvent(self, event):
        '''Overridden to emit a useful signal.'''
        super().resizeEvent(event)
        self.resized.emit(self.size())


class ImagePicker(QMainWindow):
    '''Simple viewer and chooser application for pictures.'''

    scrollArea: ResizeEmittingScrollArea = None
    filmstrip: QWidget = None

    actions: Actions = None
    buttons: Buttons = None
    labels: Labels = None
    model: PickerModel = None

    _imagesLoaded: bool = False

    # signals -- this is going to make pylint complain, but whatever
    imageChanged = pyqtSignal(int)
    inputSelected = pyqtSignal(str)
    outputSelected = pyqtSignal(str)
    countUpdated = pyqtSignal(int)
    pickedUpdated = pyqtSignal(int)

    def __init__(self):
        super().__init__()

        self.model = PickerModel()
        self._initUI()
        self._connectSlots()
        self._createActions()
        self._createMenus()

        self.setWindowTitle("ImagePicker")
        self.resize(800, 500)

    def _initUI(self):
        # buttons
        prevBtn = QPushButton('« Previous')
        prevBtn.setBackgroundRole(QPalette.Base)

        nextBtn = QPushButton('Next »')
        nextBtn.setBackgroundRole(QPalette.Base)

        pickBtn = QPushButton('...')
        pickBtn.setBackgroundRole(QPalette.Base)

        self.buttons = Buttons(previous=prevBtn, next=nextBtn, pick=pickBtn)

        # labels
        totalLabel = QLabel()
        totalLabel.setBackgroundRole(QPalette.Base)

        pickedLabel = QLabel()
        pickedLabel.setBackgroundRole(QPalette.Base)

        inputLabel = QLabel()
        inputLabel.setBackgroundRole(QPalette.Base)

        outputLabel = QLabel()
        outputLabel.setBackgroundRole(QPalette.Base)

        mainImageLabel = QLabel()
        mainImageLabel.setBackgroundRole(QPalette.Dark)
        mainImageLabel.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        mainImageLabel.setScaledContents(True)

        prevStripImage = QLabel()
        prevStripImage.setBackgroundRole(QPalette.Dark)
        # prevStripImage.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        # prevStripImage.setScaledContents(True)

        currStripImage = QLabel()
        currStripImage.setBackgroundRole(QPalette.Dark)
        # currStripImage.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        # currStripImage.setScaledContents(True)

        nextStripImage = QLabel()
        nextStripImage.setBackgroundRole(QPalette.Dark)
        # nextStripImage.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        # nextStripImage.setScaledContents(True)

        self.labels = Labels(mainImage=mainImageLabel,
                             prevStripImage=prevStripImage,
                             currStripImage=currStripImage,
                             nextStripImage=nextStripImage,
                             total=totalLabel,
                             picked=pickedLabel, output=outputLabel,
                             input=inputLabel)

        # layout time
        centerLayout = QHBoxLayout()
        scrollArea = ResizeEmittingScrollArea()
        scrollArea.setBackgroundRole(QPalette.Base)
        scrollArea.setWidget(mainImageLabel)
        self.scrollArea = scrollArea
        centerLayout.addWidget(scrollArea)
        centerLayout.setStretch(0, 2)

        filmstrip = QWidget()
        self.filmstrip = filmstrip
        filmstripLayout = QVBoxLayout(filmstrip)
        filmstripLayout.addWidget(prevStripImage)
        filmstripLayout.addWidget(currStripImage)
        filmstripLayout.addWidget(nextStripImage)
        filmstrip.setMinimumWidth(75)
        filmstrip.setMaximumWidth(150)
        centerLayout.addWidget(filmstrip)

        vLayout = QVBoxLayout()
        vLayout.addLayout(centerLayout)
        vLayout.setStretch(0, 3)

        labelGrid = QHBoxLayout()
        labelGrid.addWidget(totalLabel)
        labelGrid.addWidget(pickedLabel)
        labelGrid.addWidget(inputLabel)
        labelGrid.addWidget(outputLabel)
        vLayout.addLayout(labelGrid)

        buttonSet = QHBoxLayout()
        buttonSet.addWidget(prevBtn)
        buttonSet.addWidget(pickBtn)
        buttonSet.addWidget(nextBtn)
        vLayout.addLayout(buttonSet)

        # turns out we need to do this because the QMainWindow can't have its
        # layout manually set (or, at least, I don't know how)
        window = QWidget()
        window.setLayout(vLayout)

        self.setCentralWidget(window)

    def _connectSlots(self):
        self.inputSelected.connect(
            lambda s: self.labels.input.setText('In: ' + s))
        self.outputSelected.connect(
            lambda s: self.labels.output.setText('Out: ' + s))
        self.countUpdated.connect(
            partial(updateCountLabel, self.labels.total, 'Total'))
        self.pickedUpdated.connect(
            partial(updateCountLabel, self.labels.picked, 'Picked'))
        self.pickedUpdated.connect(self._updatePickedButton)
        self.imageChanged.connect(self._updateDisplay)
        self.scrollArea.resized.connect(self._scaleImages)

        self.buttons.pick.clicked.connect(self._toggle)
        self.buttons.previous.clicked.connect(self._retreat)
        self.buttons.next.clicked.connect(self._advance)

    def _createActions(self):
        _open = QAction("&Open...", self, shortcut="Ctrl+O",
                        triggered=self._open)
        _save = QAction("&Save to File...", self, shortcut="Ctrl+S",
                        triggered=self._save)
        _exit = QAction("E&xit", self, shortcut="Ctrl+Q", triggered=self.close)
        _about = QAction("&About", self, triggered=self._about)
        _scaleToFullSize = QAction("&Scale to Full Size", self,
                                   shortcut="Ctrl+F", enabled=False,
                                   triggered=self._scaleToFullSize)
        _fitToWindow = QAction("&Fit to Window", self, enabled=False,
                               checkable=True, shortcut="Ctrl+W",
                               triggered=self._fitToWindow)

        self.actions = Actions(open=_open, save=_save, exit=_exit,
                               about=_about, scaleToFullSize=_scaleToFullSize,
                               fitToWindow=_fitToWindow)

    def _createMenus(self):
        _file = QMenu("&File", self)
        _file.addAction(self.actions.open)
        _file.addAction(self.actions.save)
        _file.addSeparator()
        _file.addAction(self.actions.exit)

        _view = QMenu("&View", self)
        _view.addAction(self.actions.scaleToFullSize)
        _view.addSeparator()
        _view.addAction(self.actions.fitToWindow)

        _help = QMenu("&Help", self)
        _help.addAction(self.actions.about)

        menuBar = self.menuBar()
        # menuBar.setNativeMenuBar(False)
        menuBar.addMenu(_file)
        menuBar.addMenu(_view)
        menuBar.addMenu(_help)

    def _open(self):
        dialog = QFileDialog(self, "Open File / Directory", QDir.currentPath(),
                             "YAML (*.yml *.yaml)")
        dialog.exec_()
        results = dialog.selectedFiles()
        if not results:
            return

        self.inputSelected.emit(results[0])

        self.model.load(results[0])
        if not self.model.files:
            return

        self.imageChanged.emit(self.model.currentFile)

        self.countUpdated.emit(self.model.count)
        self.pickedUpdated.emit(0)

    def _toggle(self):
        self.model.toggle()
        self.pickedUpdated.emit(self.model.pickedCount)
        self.model.save()

    def _save(self):
        fileName, _ = QFileDialog.getSaveFileName(
            self, 'Save File', QDir.currentPath(), 'YAML (*.yml *.yaml)')
        if not fileName:
            return

        self.model.outfile = fileName
        self.model.save()
        self.outputSelected.emit(fileName)

    def _updateDisplay(self):
        fileName = self.model.currentFile
        image = QImage(fileName)
        if image.isNull():
            QMessageBox.information(self, "ImagePicker",
                                    "Can't load {}".format(fileName))
            return

        self.labels.mainImage.setPixmap(QPixmap.fromImage(image))

        if not self._imagesLoaded:
            self.labels.currStripImage.setStyleSheet('border: 2px solid blue')
            self.buttons.pick.setText(None)
            self._imagesLoaded = True

        filmstripWidth = self.filmstrip.width()
        for fileName, labelName in [('prevFile', 'prevStripImage'),
                                    ('currentFile', 'currStripImage'),
                                    ('nextFile', 'nextStripImage')]:
            file_ = getattr(self.model, fileName)
            label_ = getattr(self.labels, labelName)
            image = QImage(file_)
            if image.isNull():
                QMessageBox.information(self, "ImagePicker",
                                        "Can't load {}".format(file_))
            pixmap = QPixmap.fromImage(image).scaledToWidth(filmstripWidth)
            label_.setPixmap(pixmap)

        self.actions.fitToWindow.setEnabled(True)
        self._updateActions()

        self._updatePickedButton()

        self._scaleImages()

    def _updatePickedButton(self):
        pickBtn = self.buttons.pick
        if self.model.isPicked():
            pickBtn.setIcon(ICON_DELETE)
        else:
            pickBtn.setIcon(ICON_HEART)

    def _advance(self):
        self.model.advance()
        self.imageChanged.emit(self.model.currentFile)

    def _retreat(self):
        self.model.retreat()
        self.imageChanged.emit(self.model.currentFile)

    def _about(self):
        info = '''<p>
        The ImagePicker application allows you to load up a directory
        tree and mark images as picked, or load up a file of previously picked
        images and further filter down the set.
        </p>'''

        QMessageBox.about(self, "About ImagePicker", info)

    def _scaleToFullSize(self):
        self.labels.mainImage.adjustSize()

    def _scaleToWindowSize(self):
        imageSize = self.labels.mainImage.pixmap().size()
        scrollAreaSize = self.scrollArea.size()
        scaled = imageSize.scaled(scrollAreaSize, Qt.KeepAspectRatio)
        self.labels.mainImage.resize(scaled)

    def _fitToWindow(self):
        shouldFit = self.actions.fitToWindow.isChecked()
        # self.scrollArea.setWidgetResizable(shouldFit)
        if not shouldFit:
            self._scaleToFullSize()
        else:
            self._scaleToWindowSize()

        self._updateActions()

    def _updateActions(self):
        self.actions.scaleToFullSize.setEnabled(
            not self.actions.fitToWindow.isChecked())

    def _scaleImages(self, *_):
        if self.actions.fitToWindow.isChecked():
            self._scaleToWindowSize()
        else:
            self._scaleToFullSize()

    def _adjustScrollBars(self, scale):
        for scb in [self.scrollArea.horizontalScrollBar(),
                    self.scrollArea.verticalScrollBar()]:
            adjustment = computeScrollBarAdjustment(scb, scale)
            scb.setValue(int(adjustment))
