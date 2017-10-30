#-*- coding: utf-8 -*-
'''
Holding the state for the application.
'''
import os
import typing as T

from ruamel.yaml import YAML
from imagepicker.utils import listImageFiles


class PickerModel:
    '''Maintain the state for the ImagePicker.'''

    files: T.List[str]
    picked: T.Set[str]
    outfile: str
    infile: str
    current: int

    def __init__(self, infile: str=None, outfile: str=None) -> None:
        '''Initialize the model.'''
        if infile is not None:
            self.load(infile)

        self.outfile = outfile

    def isPicked(self, filename: str=None) -> bool:
        '''Is the given file (or current file) picked?'''
        if not filename:
            filename = self.currentFile
        return filename in self.picked

    def pick(self, filename: str=None) -> None:
        '''Select the given (or current) file.'''
        if not filename:
            filename = self.currentFile
        self.picked.add(filename)

    def unpick(self, filename: str=None) -> None:
        '''Un-select the given (or current) file.'''
        if not filename:
            filename = self.currentFile
        try:
            self.picked.remove(filename)
        except KeyError:
            pass

    def toggle(self, filename: str=None) -> None:
        '''Select or un-select the given (or current) file.'''
        if not filename:
            filename = self.currentFile
        if filename in self.picked:
            self.unpick(filename)
        else:
            self.pick(filename)

    def load(self, filename: str) -> None:
        '''Initialize our state from the given filename or directory.'''
        self.infile = filename

        if os.path.isdir(filename):
            self._loadDir(filename)
        else:
            self._loadFile(filename)

        self.picked = set()
        self.current = 0

    def _loadFile(self, filename: str) -> None:
        '''Load image list from a YAML file.'''
        yaml = YAML(typ='safe')
        with open(filename, 'r') as f:
            contents = yaml.load(f)

        if 'images' not in contents:
            raise AssertionError('Input file not properly formatted!')

        self.files = contents['images']

    def _loadDir(self, dirname: str) -> None:
        '''Load image list from a directory tree.'''
        self.files = list(listImageFiles(dirname))

    def save(self) -> None:
        '''Write the image list to a YAML file.'''
        if not self.outfile:
            return

        yaml = YAML()
        with open(self.outfile, 'w') as f:
            yaml.dump({'images': sorted(self.picked)}, f)

    @property
    def currentFile(self) -> str:
        '''Return the filename of the current file.'''
        return self.files[self.current]

    @property
    def nextFile(self) -> str:
        '''What's the upcoming file?'''
        return self.files[(self.current + 1) % len(self.files)]

    @property
    def prevFile(self) -> str:
        '''What's the last file?'''
        return self.files[(self.current - 1) % len(self.files)]

    @property
    def count(self) -> int:
        '''How many files do we have in total?'''
        return len(self.files)

    @property
    def pickedCount(self) -> int:
        '''How many files have been picked?'''
        return len(self.picked)

    def advance(self) -> None:
        '''Step to the next file, wrapping around if we go over the end.'''
        self.current += 1
        if self.current >= len(self.files):
            self.current = 0

    def retreat(self) -> None:
        '''Step to previous file, wrapping around if we go past the start.'''
        self.current -= 1
        if self.current < 0:
            self.current = len(self.files) - 1
