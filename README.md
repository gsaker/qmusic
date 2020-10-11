# QMusic

QMusic is a simple application for audio playback written in Python using the PySide2 Qt5 framework.

*Please note: PySide2 version 5.14 or lower is required as of now due to a bug in QtMultimedia leading to QUrls containing spaces not working in Qt 5.15.*


# Dependencies

Python 3.5 or newer, with `python` or `python3` available in your path.

`python3 setup.py install` - install the required packages

There is a token for the lyrics from Genius located at `resources/lyricsgenius_token.txt`, however if the token in here is invalid, you can replace it with your own by using the Genius API from their website. The documentation can also be found in `reference.txt`.


# Running

`python3 setup.py run` - run the program using the Python interpreter


# Screenshots

<img src="resources/documentation/screenshot.png" width=320 style="border-radius: 4px; margin-bottom: 10px"/>


# Other Environment Commands

`python3 setup.py clean` - clean the build environment

`python3 setup.py py2app -A` - build a macOS app package

`python3 setup.py compile` - build a Windows executable

`sudo python3 setup.py install_unix` - write a script to /usr/local/bin on Unix-like systems from which QMusic can be run

For more info, run `python3 setup.py --help`

For more commands, run `python3 setup.py --help-commands`

_______________________

**Please note, compilation is currently broken due to Nuitka not supporting PySide2/Shiboken2.**

~~`python3 setup.py compile` - transpile the Python program to C and compile it to binary using Nuitka~~

~~`python3 setup.py run -e` - run the binary~~

~~`python3 setup.py compile -m` - build an application for macOS~~

~~`python3 setup.py run -m` - run the macOS application~~
