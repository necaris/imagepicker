#-*- coding: utf-8 -*-
'''
Define the UI
'''
from functools import partial
import logging
import time
import typing as T

from PyQt5 import QtCore, QtGui
from PyQt5.QtCore import Qt, QDir, QSize, QTimer, pyqtSignal, QEvent, QObject
from PyQt5.QtGui import QImage, QPalette, QPixmap, QIcon
from PyQt5.QtWidgets import (QAction, QFileDialog, QLabel,
                             QMainWindow, QMenu, QMessageBox, QScrollArea,
                             QSizePolicy, QHBoxLayout, QVBoxLayout,
                             QPushButton, QWidget, QInputDialog)

from imagepicker.model import PickerModel
from imagepicker.utils import (computeScrollBarAdjustment, updateCountLabel)
# side-effect-ful import initializes the image resources we know about
import imagepicker.resources


ICON_HEART = QIcon(':/images/heart.svg')
ICON_DELETE = QIcon(':/images/delete.svg')
# TODO: Add some more appropriate icons for rotation, put-into-album, etc


# TODO: We wanna rotate! Will need a rotate button / action, possibly some
# way to save the image back (sadface)
# QPixmap pixmap(*my_label->pixmap());
# QMatrix rm;
# rm.rotate(90);
# pixmap = pixmap.transformed(rm);
# my_label->setPixmap(pixmap);

# -- for saving it back, see https://doc.qt.io/qt-5/qimagewriter.html#write

# TODO: we're going to need:
# - an albums area in the filmstrip
#   - an 'add album' button, and a 'remove album' I guess

# - add rotation, as above
#   - perform the rotation(s), save the rotated image?
#   - buttons in the center to do this, between Prev and Next
#   - add actions for this
# - optimize?

UIActions = T.NamedTuple('Actions',
                       [('open', QAction), ('save', QAction), ('exit', QAction),
                        ('about', QAction), ('scaleToFullSize', QAction),
                        ('fitToWindow', QAction), ('addAlbum', QAction),
                        ('removeAlbum', QAction)])

Buttons = T.NamedTuple('Buttons',
                       [('previous', QPushButton), ('next', QPushButton),
                        ('albums', T.Dict[str, QPushButton]),
                        ('addAlbum', QPushButton), ('removeAlbum', QPushButton)])


Labels = T.NamedTuple('Labels',
                      [('mainImage', QLabel), ('prevStripImage', QLabel),
                       ('currStripImage', QLabel), ('nextStripImage', QLabel),
                       ('total', QLabel), ('picked', QLabel),
                       ('input', QLabel), ('output', QLabel),
                       ])


class ResizeEmittingScrollArea(QScrollArea):
    '''QScrollArea that informs us on resize, so we can take action.'''
    resized = pyqtSignal(QSize)

    def resizeEvent(self, event: T.Any) -> None:
        '''Overridden to emit a useful signal.'''
        super().resizeEvent(event)
        self.resized.emit(self.size())


class ImagePicker(QMainWindow):
    '''Simple viewer and chooser application for pictures.'''

    scrollArea: ResizeEmittingScrollArea = None
    filmstrip: QWidget = None

    uiActions: UIActions = None
    buttons: Buttons = None
    labels: Labels = None

    _albumButtonLayout: QVBoxLayout = None

    _model: PickerModel = None
    logger: logging.Logger = None
    _imagesLoaded: bool = False
    _imageCache: T.Dict = None

    # signals -- this is going to make pylint complain, but whatever
    imageChanged = pyqtSignal(int)
    inputSelected = pyqtSignal(str)
    outputSelected = pyqtSignal(str)
    albumAdded = pyqtSignal(str)
    albumRemoved = pyqtSignal(str)
    imageToggled = pyqtSignal(str, str)

    @property
    def model(self) -> PickerModel:
        if not self._model:
            self._initModel()

        return self._model

    def __init__(self, logger: logging.Logger=None) -> None:
        super().__init__()

        self.logger = logger
        self._imageCache = {}
        self._initUI()
        self._connectSlots()
        self._createActions()
        self._createMenus()

        # And now, after creating everything, we wait a beat and then load up
        # the model data
        QTimer.singleShot(250, self._initModel)

    def _initModel(self) -> None:
        dialog = QFileDialog(self, "Input directory to browse", QDir.currentPath(),
                             "")
        dialog.exec_()
        results = dialog.selectedFiles()
        if not results:
            QMessageBox.critical(self, 'ImagePicker', 'Must choose input directory!')

        inputDirectory = results[0]

        fileName, _ = QFileDialog.getSaveFileName(
            self, 'Open Album List', QDir.currentPath(), 'YAML (*.yml *.yaml)')
        if not fileName:
            QMessageBox.critical(self, "ImagePicker", "Must choose album file!")

        self._model = PickerModel(fileName, inputDirectory)

        for n in self.model.albumNames:
            self._addAlbumButton(n)

        self.inputSelected.emit(inputDirectory)
        self.outputSelected.emit(fileName)
        self.imageChanged.emit(0)

    def _initButtons(self) -> None:
        prevBtn = QPushButton('« Previous')
        prevBtn.setBackgroundRole(QPalette.Base)

        nextBtn = QPushButton('Next »')
        nextBtn.setBackgroundRole(QPalette.Base)

        addAlbumBtn = QPushButton(' + ')
        removeAlbumBtn = QPushButton(' - ')
        self.buttons = Buttons(previous=prevBtn, next=nextBtn, albums={}, addAlbum=addAlbumBtn, removeAlbum=removeAlbumBtn)

    def _addAlbumButton(self, name: str) -> None:
        btn = QPushButton(name)  # NOTE: the text will be updated anyway
        btn.setCheckable(True)
        self.buttons.albums[name] = btn
        self._albumButtonLayout.addWidget(btn)
        # hook up the action while we're here
        btn.clicked.connect(partial(self._toggle, name))

    def _removeAlbumButton(self, name: str) -> None:
        self.logger.warning('we did the remove %s', name, self.buttons.albums[name], self.buttons.albums[name].text)
        btn = self.buttons.albums[name]
        self._albumButtonLayout.removeWidget(btn)
        del self.buttons.albums[name]
        btn.hide()
        btn.deleteLater()
        self.model.removeAlbum(name)

    def _initLabels(self) -> None:
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

    def _initLayout(self) -> None:
        # layout time
        centerLayout = QHBoxLayout()
        scrollArea = ResizeEmittingScrollArea()
        scrollArea.setBackgroundRole(QPalette.Base)
        scrollArea.setWidget(self.labels.mainImage)
        self.scrollArea = scrollArea
        centerLayout.addWidget(scrollArea)
        centerLayout.setStretch(0, 2)

        filmstrip = QWidget()
        self.filmstrip = filmstrip
        filmstripLayout = QVBoxLayout(filmstrip)
        filmstripLayout.addWidget(self.labels.prevStripImage)
        filmstripLayout.addWidget(self.labels.currStripImage)
        filmstripLayout.addWidget(self.labels.nextStripImage)
        filmstrip.setMinimumWidth(75)
        filmstrip.setMaximumWidth(150)
        centerLayout.addWidget(filmstrip)

        albumButtonLayout = QVBoxLayout()
        albumButtonLayout.setSpacing(0)
        albumButtonLayout.addWidget(self.buttons.addAlbum)
        albumButtonLayout.addWidget(self.buttons.removeAlbum)
        filmstripLayout.addLayout(albumButtonLayout)

        self._albumButtonLayout = albumButtonLayout

        vLayout = QVBoxLayout()
        vLayout.addLayout(centerLayout)
        vLayout.setStretch(0, 3)

        labelGrid = QHBoxLayout()
        labelGrid.addWidget(self.labels.total)
        labelGrid.addWidget(self.labels.picked)
        labelGrid.addWidget(self.labels.input)
        labelGrid.addWidget(self.labels.output)
        vLayout.addLayout(labelGrid)

        buttonSet = QHBoxLayout()
        buttonSet.addWidget(self.buttons.previous)
        buttonSet.addWidget(self.buttons.next)
        vLayout.addLayout(buttonSet)

        # turns out we need to do this because the QMainWindow can't have its
        # layout manually set (or, at least, I don't know how)
        window = QWidget()
        window.setLayout(vLayout)

        self.setCentralWidget(window)

    def _initUI(self) -> None:
        self._initButtons()
        self._initLabels()
        self._initLayout()

        self.setWindowTitle("ImagePicker")
        self.resize(800, 500)

    def _connectSlots(self) -> None:
        self.inputSelected.connect(
            lambda s: self.labels.input.setText('In: ' + s))
        self.outputSelected.connect(
            lambda s: self.labels.output.setText('Out: ' + s))
        self.imageChanged.connect(self._updateDisplay)
        self.scrollArea.resized.connect(self._scaleImages)

        self.albumAdded.connect(self._updateDisplay)
        self.albumRemoved.connect(self._updateDisplay)
        self.imageToggled.connect(self._toggleImage)

        self.buttons.previous.clicked.connect(self._retreat)
        self.buttons.next.clicked.connect(self._advance)
        self.buttons.addAlbum.clicked.connect(self._addAlbum)
        self.buttons.removeAlbum.clicked.connect(self._removeAlbum)

    def eventFilter(self, obj, event):
        if event.type() == QEvent.KeyPress:
            return self._handleKeyPress(event.key())
        return super().eventFilter(obj, event)

    def _handleKeyPress(self, key):
        rv = True
        if key == QtCore.Qt.Key_Right:
            self._advance()
        elif key == QtCore.Qt.Key_Left:
            self._retreat()
        else:
            rv = False
        return rv

    def _createActions(self) -> None:
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
        _addAlbum = QAction("Add Al&bum...", self, shortcut="Ctrl+B",
                            triggered=self._addAlbum)

        _removeAlbum = QAction("&Remove Album...", self, shortcut="Ctrl+R",
                               triggered=self._removeAlbum)

        self.actions = UIActions(open=_open, save=_save, exit=_exit,
                                 about=_about, scaleToFullSize=_scaleToFullSize,
                                 fitToWindow=_fitToWindow, addAlbum=_addAlbum,
                                 removeAlbum=_removeAlbum)

    def _createMenus(self) -> None:
        _file = QMenu("&File", self)
        _file.addAction(self.actions.open)
        _file.addAction(self.actions.save)
        _file.addAction(self.actions.addAlbum)
        _file.addAction(self.actions.removeAlbum)
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

    def _open(self) -> None:
        dialog = QFileDialog(self, "Open File / Directory", QDir.currentPath(),
                             "YAML (*.yml *.yaml)")
        dialog.exec_()
        results = dialog.selectedFiles()
        if not results:
            return

        self.inputSelected.emit(results[0])

        self.model.loadDirectory(results[0])
        if not self.model.inputFiles:
            return

        self.imageChanged.emit(self.model.currentFile)

    def _toggle(self, album: str) -> None:
        self.logger.debug('Toggled %s in %s', self.model.currentFile, album)
        self.model.toggle(album)
        self.model.save()
        self.imageToggled.emit(album, self.model.currentFile)
        self.logger.debug(' - toggling complete')

        self.logger.debug("album button text: %s, count %s",
                          self.buttons.albums[album].text,
                          self.model.albumCount(album))

    def _save(self) -> None:
        fileName, _ = QFileDialog.getSaveFileName(
            self, 'Save File', QDir.currentPath(), 'YAML (*.yml *.yaml)')
        if not fileName:
            return

        self.model.settingsFile = fileName
        self.model.save()
        self.outputSelected.emit(fileName)

    def _addAlbum(self) -> None:
        if not self.model.inputDir:
            QMessageBox.critical(self, 'Error', 'No input directory selected')
            return

        name, _ = QInputDialog.getText(self, 'Add Album', 'Name:')
        if not name:
            QMessageBox.critical(self, 'Error', 'No album name specified!')
            return
        dirname, _ = QInputDialog.getText(self, 'Add Album', 'Directory:')
        if not dirname:
            QMessageBox.critical(self, 'Error', 'No directory name specified!')
            return

        self.model.addAlbum(name, dirname)
        self._addAlbumButton(name)
        self.albumAdded.emit(name)

    def _removeAlbum(self) -> None:
        if not self.model.inputDir:
            QMessageBox.critical(self, 'Error', 'No input directory selected')
            return

        name, _ = QInputDialog.getText(self, 'Remove Album', 'Name:')
        if not name:
            QMessageBox.critical(self, 'Error', 'No album name specified!')
            return
        if name not in self.model.albums:
            QMessageBox.critical(self, 'Error', '{} not in current album list!'.format(name))
            return

        self.model.removeAlbum(name)
        self._removeAlbumButton(name)
        self.albumRemoved.emit(name)

    def _toggleImage(self, album: str, filename: str) -> None:
        # TODO: we should probably not `_updateDisplay`, but rather update
        # some part of the display -- we need a separate method to update non-
        # image labels and buttons
        self.logger.info('toggled: %s in %s', filename, album)
        self._updateDisplay()

    def _updateDisplay(self) -> None:
        fileName = self.model.currentFile
        pixmap = self._loadImageFromCache(fileName)

        self.labels.mainImage.setPixmap(pixmap)
        self._scaleImages()

        if not self._imagesLoaded:
            self.labels.currStripImage.setStyleSheet('border: 2px solid blue')
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
            pixmap = self._loadImageFromCache(file_).scaledToWidth(filmstripWidth)
            label_.setPixmap(pixmap)

        self.actions.fitToWindow.setEnabled(True)
        self._updateActions()

        self.labels.total.setText('{} of {}'.format(self.model.current, self.model.count))
        self._updateAlbumButtons()

    def _updateAlbumButtons(self) -> None:
        for name in self.model.albumNames:
            btn = self.buttons.albums[name]
            btn.setChecked(self.model.isPicked(name))

    def _advance(self) -> None:
        self.model.advance()
        self.imageChanged.emit(self.model.currentFile)

    def _retreat(self) -> None:
        self.model.retreat()
        self.imageChanged.emit(self.model.currentFile)

    def _about(self) -> None:
        info = '''<p>
        The ImagePicker application allows you to load up a directory
        tree and mark images as picked, or load up a file of previously picked
        images and further filter down the set.
        </p>'''

        QMessageBox.about(self, "About ImagePicker", info)

    def _scaleToFullSize(self) -> None:
        self.labels.mainImage.adjustSize()

    def _scaleToWindowSize(self) -> None:
        imageSize = self.labels.mainImage.pixmap().size()
        scrollAreaSize = self.scrollArea.size()
        scaled = imageSize.scaled(scrollAreaSize, Qt.KeepAspectRatio)
        self.labels.mainImage.resize(scaled)

    def _fitToWindow(self) -> None:
        shouldFit = self.actions.fitToWindow.isChecked()
        # self.scrollArea.setWidgetResizable(shouldFit)
        if not shouldFit:
            self._scaleToFullSize()
        else:
            self._scaleToWindowSize()

        self._updateActions()

    def _updateActions(self) -> None:
        self.actions.scaleToFullSize.setEnabled(
            not self.actions.fitToWindow.isChecked())

    def _scaleImages(self, *_: T.Any) -> None:
        if self.actions.fitToWindow.isChecked():
            self._scaleToWindowSize()
        else:
            self._scaleToFullSize()

    def _adjustScrollBars(self, scale: float) -> None:
        for scb in [self.scrollArea.horizontalScrollBar(),
                    self.scrollArea.verticalScrollBar()]:
            adjustment = computeScrollBarAdjustment(scb, scale)
            scb.setValue(int(adjustment))

    def _loadImageFromCache(self, filename: str) -> QPixmap:
        self.logger.debug('%s', filename)
        if filename in self._imageCache:
            pixmap, _ = self._imageCache[filename]
            self.logger.debug(' - found in cache')
            return pixmap

        self.logger.debug(' - not in cache')
        image = QImage(filename)
        if image.isNull():
            QMessageBox.information(self, "ImagePicker",
                                    "Can't load {}".format(filename))

        self.logger.debug(' - loaded QImage: %s', image)
        pixmap = QPixmap.fromImage(image)
        self.logger.debug(' - loaded QPixmap: %s', pixmap)
        self._imageCache[filename] = (pixmap, time.time())

        # cache pruning
        if len(self._imageCache) > 5:
            lru = sorted(self._imageCache.keys(),
                         key=lambda k: self._imageCache[k][1])[0]
            del self._imageCache[lru]
            self.logger.debug(' - pruned cache')

        return pixmap
