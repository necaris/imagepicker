#-*- coding: utf-8 -*-
'''
Holding the state for the application.
'''
import os
from os.path import join, abspath, relpath, exists, isdir, islink, isabs, basename
import typing as T

from ruamel.yaml import YAML
from imagepicker.utils import listImageFiles, setPDBTrace


# TODO: we're going to need caching and such to see how many things are
# in each album, and so on, instead of O(n) len(os.listdir()) calls...


class PickerModel:
    '''Maintain the state for the ImagePicker.'''

    albums: T.Dict[str, str]
    inputDir: str
    inputFiles: T.List[str]
    settingsFile: str
    current: int

    def __init__(self, settingsFile: str, inputDirectory: str) -> None:
        '''Initialize the model.'''
        self.current = 0

        self.loadDirectory(inputDirectory)
        self.loadSettings(settingsFile)

    def loadSettings(self, settingsPath: str) -> None:
        self.settingsFile = settingsPath

        if exists(settingsPath):
            yaml = YAML(typ='safe')
            with open(settingsPath, 'r') as f:
                contents = yaml.load(f)

            if 'albums' not in contents:
                raise AssertionError('Settings file not correctly formatted!')
        else:
            contents = {'albums': {}}

        self.albums = {}
        for name, path in contents['albums'].items():
            self.addAlbum(name, path)

    def loadDirectory(self, dirname: str) -> None:
        '''Load image list from a directory tree.'''
        self.inputDir = dirname
        self.inputFiles = list(listImageFiles(dirname))

    def addAlbum(self, name: str, dirname: str) -> None:
        if not isabs(dirname):
            dirname = abspath(join(self.inputDir, dirname))
        if not isdir(dirname):
            os.makedirs(dirname)
        self.albums[name] = dirname
        self.save()

    def removeAlbum(self, name: str) -> None:
        # TODO: Do we clear out the directory when we remove the album?
        if name in self.albums:
            del self.albums[name]
        self.save()

    def isPicked(self, album: str, filename: str=None):
        if album not in self.albums:
            raise KeyError('No such album: {}'.format(album))

        if not filename:
            filename = self.currentFile
        return islink(join(self.albums[album], basename(filename)))

    def pick(self, album: str, filename: str=None) -> None:
        '''Select the given (or current) file.'''
        if not filename:
            filename = self.currentFile

        try:
            albumPath = self.albums[album]
            filePath = filename if isabs(filename) else abspath(join(self.inputDir, filename))
            baseFileName = basename(filename)
            os.symlink(filePath, join(albumPath, baseFileName))
        except FileExistsError:
            pass

    def unpick(self, album: str, filename: str=None) -> None:
        '''Un-select the given (or current) file.'''
        if not filename:
            filename = self.currentFile

        baseFileName = basename(filename)
        filePath = abspath(join(self.albums[album], baseFileName))
        if not exists(filePath):
            return

        try:
            os.remove(filePath)
        except OSError:
            pass

    def toggle(self, album: str, filename: str=None) -> None:
        '''Select or un-select the given (or current) file.'''
        if not filename:
            filename = self.currentFile
        if self.isPicked(album, filename):
            self.unpick(album, filename)
        else:
            self.pick(album, filename)

    def save(self) -> None:
        '''Write the album list to a YAML file.'''
        if not self.settingsFile:
            return

        yaml = YAML()
        with open(self.settingsFile, 'w') as f:
            yaml.dump({'albums': self.albums}, f)

    @property
    def albumNames(self) -> T.List[str]:
        return sorted(self.albums.keys())

    def _fullPath(self, filename: str) -> None:
        if not isabs(filename):
            filename = abspath(join(self.inputDir, filename))

        return filename

    @property
    def currentFile(self) -> str:
        '''Return the filename of the current file.'''
        return self._fullPath(self.inputFiles[self.current])

    @property
    def nextFile(self) -> str:
        '''What's the upcoming file?'''
        return self._fullPath(self.inputFiles[(self.current + 1) % len(self.inputFiles)])

    @property
    def prevFile(self) -> str:
        '''What's the last file?'''
        return self._fullPath(self.inputFiles[(self.current - 1) % len(self.inputFiles)])

    @property
    def count(self) -> int:
        '''How many files do we have in total?'''
        return len(self.inputFiles)

    def albumCount(self, name) -> int:
        albumPath = self.albums[name]
        return len(os.listdir(albumPath))

    def advance(self) -> None:
        '''Step to the next file, wrapping around if we go over the end.'''
        self.current += 1
        if self.current >= len(self.inputFiles):
            self.current = 0

    def retreat(self) -> None:
        '''Step to previous file, wrapping around if we go past the start.'''
        self.current -= 1
        if self.current < 0:
            self.current = len(self.inputFiles) - 1
