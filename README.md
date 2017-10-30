# PyQt5 Image Viewer / Picker

Loads a directory tree of images and allows them to be viewed (with fit-to-window and full-size views) and 'selected' -- selected images can be written to a YAML file to save the list. The output YAML file can also be loaded as an input, allowing further filtering of the tree.

Developed as a weekend hack for filtering down a giant pile of images to a few unique albums' worth. Heavily derived from the PyQt5 image viewer example at https://github.com/baoboa/pyqt5/blob/master/examples/widgets/imageviewer.py

### TODO:
- Tests
- Performance optimization -- reusing already-loaded images where possible
- Some actual UI design tips might be nice
- Refactoring for verbosity, particularly `ui.py`
