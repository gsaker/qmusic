#
#   widgets.py
#   Classes for widgets and windows
#

from PySide2 import QtWidgets, QtCore, QtGui, QtMultimedia
import lib
import os
from playlist import PlaylistModel, PlaylistView
import mutagen
from typing import List
import threading
import time

is_admin = lib.get_admin_status()
if is_admin:
    import keyboard

class MainWindow(QtWidgets.QMainWindow):
    #   -   init: 
    #       -   Call init on super
    #       -   Set geometry variables
    #       -   Set app from QApplication parameter
    #       -   Set player fade rates
    #       -   Call initUI
    #   -   initUI:
    #       -   Set geometry and title
    #       -   Set variable with path to executable to find resources later on
    #       -   Create widgets: buttons for media controls, labels, sliders
    #       -   Initialise player, connect to time and volume sliders
    #       -   Set to paused state
    #       -   Update the duration to 0
    #       -   Initialise playlist
    #       -   Add widgets to layout
    #       -   Create central widget and set layout on central widget
    #       -   Create menus and shortcuts
    #       -   Add media from config, reset lastMediaCount, isTransitioning, isFading and lastVolume variables
    #       -   Set variables for fade out and in rates
    #       -   Show

    def __init__(self, app: QtWidgets.QApplication):
        super().__init__()
        self.left = 0
        self.top = 0
        self.width = lib.rootWidth
        self.height = lib.rootHeight
        self.title = lib.progName
        self.app = app

        self.rate_ms_fadeOut = 200
        self.rate_ms_fadeIn = 200
        
        self.initUI()

    def initUI(self):
        self.setGeometry(self.left, self.top, self.width, self.height)
        self.setWindowTitle(self.title)

        self.createWidgets()
        self.initPlayer()
        self.initPlaylist()
        self.init_playpause()
        self.connect_update_media()
        self.createLayout()
        self.createCentralWidget()
        self.createMenus()
        self.createShortcuts()

        self.addMediaFromConfig()
        self.lastMediaCount = 0
        self.isTransitioning = False
        self.isFading = False
        self.lastVolume = self.player.volume()

        self.show()

    def createWidgets(self):
        # Create buttons, labels and sliders
        self.control_playpause = QtWidgets.QPushButton()
        self.control_playpause.setFixedWidth(85)
        self.control_previous = QtWidgets.QPushButton(self.tr("Previous"))
        self.control_next = QtWidgets.QPushButton(self.tr("Next"))

        self.volumeSlider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.volumeSlider.setMaximum(100)
        self.volumeSlider.setValue(100)
        
        self.timeSlider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.timePositionLabel = QtWidgets.QLabel(lib.to_hhmmss(0))
        self.totalTimeLabel = QtWidgets.QLabel(lib.to_hhmmss(0))
        self.timePositionLabel.setStyleSheet(
            "QLabel {color: #" + lib.textColour + "}"
        )
        self.totalTimeLabel.setStyleSheet(
            "QLabel {color: #" + lib.textColour + "}"
        )

        self.metadata_label = QtWidgets.QLabel()
        self.metadata_label.setStyleSheet(
            "QLabel {color: #" + lib.textColour + "}"
        )
        self.metadata_label.hide()

        self.coverart_label = QtWidgets.QLabel()
        self.coverart_label.hide()
        self.coverart_width = 64

        # Create playlist action buttons and connect pressed signals
        self.control_playlist_moveDown = QtWidgets.QPushButton(self.tr("Move Down"))
        self.control_playlist_moveUp = QtWidgets.QPushButton(self.tr("Move Up"))
        self.control_playlist_remove = QtWidgets.QPushButton(self.tr("Remove"))
        self.control_playlist_clear = QtWidgets.QPushButton(self.tr("Clear"))

        self.control_playlist_moveDown.pressed.connect(self.playlist_moveDown)
        self.control_playlist_moveUp.pressed.connect(self.playlist_moveUp)
        self.control_playlist_remove.pressed.connect(self.removeMedia)
        self.control_playlist_clear.pressed.connect(self.playlist_clear)

    def initPlayer(self):
        # Create QMediaPlayer and connect to time and volume sliders value changed members, connect player position/duration changed to update position and duration methods
        self.player = QtMultimedia.QMediaPlayer()
        self.volumeSlider.valueChanged.connect(self.player.setVolume)

        # Note: self.player.setPosition adds pauses to playback
        self.timeSlider.valueChanged.connect(self.setPosition)
        self.player.durationChanged.connect(self.update_duration)
        self.player.positionChanged.connect(self.update_position)

    def setPosition(self, position: int):
        # Get player position and if the new slider position has changed, set the player position
        player_position = self.player.position()
        if position > player_position + 1 or position < player_position - 1:
            self.player.setPosition(position)

        # If position is near the end, fade out
        duration = self.player.duration()
        if not self.isTransitioning and position > duration - 1000:
            self.isTransitioning = True
            self.fadeOut()

        # If transitioning and the new track has started, reset the transitioning state and restore volume
        if self.isTransitioning and not self.isFading and position < duration - 1000:
            self.fadeIn()

    def fadeOut(self):
        # Run the fade out on a new thread with the function set as the target for the thread and by calling start
        self.fadeThread = threading.Thread(target=self._fadeOut)
        self.fadeThread.start()
        
    def _fadeOut(self):
        # Set the last volume and lower volume by incriment every x ms until the volume is equal to 0, exit if the track has already switched
        self.lastVolume = self.player.volume()
        volume = self.lastVolume
        self.lastTrackIndex = self.playlist.currentIndex()
        while volume != 0 and self.playlist.currentIndex() == self.lastTrackIndex:
            volume -= 1
            self.player.setVolume(volume)
            self.isFading = True
            time.sleep(1 / self.rate_ms_fadeOut)
        
        # If not fading and the track has changed, instantly restore the volume to prevent volume from staying at 0
        if not self.isFading and self.playlist.currentIndex() != self.lastTrackIndex:
            self.restoreVolume()
        
        self.isFading = False

    def fadeIn(self):
        # Run the fade in on a new thread with the function set as the target for the thread and by calling start
        self.fadeThread = threading.Thread(target=self._fadeIn)
        self.fadeThread.start()

    def _fadeIn(self):
        # Increase volume by incriment every x ms until the volume has reached the pre-fade volume, reset isTransitioning
        volume = self.player.volume()
        while volume != self.lastVolume:
            volume += 1
            self.player.setVolume(volume)
            self.isFading = True
            time.sleep(1 / self.rate_ms_fadeIn)

        self.isFading = False
        self.isTransitioning = False

    def restoreVolume(self):
        # Set the player volume to the last recorded volume
        print("Restoring volume")
        self.player.setVolume(self.lastVolume)

    def update_duration(self, duration: int):
        # Set time slider maximum and set total time label text formatted from argument
        self.timeSlider.setMaximum(duration)
        self.totalTimeLabel.setText(lib.to_hhmmss(duration))

    def update_position(self):
        # Set time slider value, refresh labels
        position = self.player.position()
        self.timeSlider.setValue(position)
        self.timePositionLabel.setText(lib.to_hhmmss(position))

    def initPlaylist(self):
        # Create QMediaPlaylist, connect to player, create and connect playlist model, connect media control pressed signals to playlist methods
        self.playlist = QtMultimedia.QMediaPlaylist()
        self.player.setPlaylist(self.playlist)
        self.playlistModel = PlaylistModel(self.playlist)
        self.control_previous.pressed.connect(self.previousTrack)
        self.control_next.pressed.connect(self.nextTrack)

        # Create playlist view and set model, create selection model from playlist view and connect playlist selection changed method
        self.playlistView = PlaylistView(self.playlistModel)
        self.playlistViewSelectionModel = self.playlistView.selectionModel()
        # self.playlistViewSelectionModel.selectionChanged.connect(self.playlist_selection_changed)

        # Set view selection mode to abstract item view extended selection and connect double click signal to switch media
        self.playlistView.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.playlistView.doubleClicked.connect(self.switchMedia)

        # Accept drag and drop
        self.setAcceptDrops(True)

    def previousTrack(self):
        self.playlist.previous()
        self.play()

    def nextTrack(self):
        self.playlist.next()
        self.play()

    def updatePlayingState(self):
        if self.isPlaying():
            self.play()
        else:
            self.pause()

    #
    #   Revise
    #

    def playlist_moveDown(self):
        # Get selected indexes on the playlist view and save the current playlist index
        selectedIndexes = self.playlistView.selectedIndexes()
        currentPlaylistIndex = self.playlist.currentIndex()

        # If there are selected indexes in the index list, the index list does not contain the current track and the index after (+1) the last selected index is larger than the current index
        if len(selectedIndexes) > 0 and selectedIndexes.__contains__(self.playlistModel.index(currentPlaylistIndex)) == False and selectedIndexes[len(selectedIndexes) - 1].row() + 1 > currentPlaylistIndex:
            # Get the first and maximum index rows
            firstIndex = selectedIndexes[0].row()
            maxIndex = selectedIndexes[len(selectedIndexes) - 1].row()

            # Get selected media
            media = self.getSelectedMedia(firstIndex, maxIndex)
            
            # Set the previous selected indexes
            previousSelectedIndexes = self.playlistView.selectedIndexes()

            # Insert all of the media in the list to 2 indexes after the current on the playlist, remove the previous original media instances from the playlist and emit the playlist model layout change signal
            self.playlist.insertMedia(firstIndex + 2, media)
            self.playlist.removeMedia(firstIndex, maxIndex)
            self.playlistModel.layoutChanged.emit()

            # On the playlist view selection model, call the select function with the selection model deselect parameter to deselect all of the items in the previus selected indexes
            len_previousSelectedIndexes = len(previousSelectedIndexes)
            self.playlistViewSelectionModel.select(QtCore.QItemSelection(previousSelectedIndexes[0], previousSelectedIndexes[len_previousSelectedIndexes - 1]), QtCore.QItemSelectionModel.Deselect)

            # On the playlist view selection model, call the select function with the selection model select parameter to select all of the moved selected indexes (all of the previous selected indexes shifted by 1 over)
            self.playlistViewSelectionModel.select(QtCore.QItemSelection(self.playlistModel.index(previousSelectedIndexes[0].row() + 1), self.playlistModel.index(previousSelectedIndexes[len_previousSelectedIndexes - 1].row() + 1)), QtCore.QItemSelectionModel.Select)

    def playlist_moveUp(self):
        # Get selected indexes on the playlist view and save the current playlist index
        selectedIndexes = self.playlistView.selectedIndexes()
        currentPlaylistIndex = self.playlist.currentIndex()
        
        # If there are selected indexes in the index list, the index list does not contain the current track and the index before (-1) the last selected index is larger than the current index
        if len(selectedIndexes) > 0 and selectedIndexes.__contains__(self.playlistModel.index(currentPlaylistIndex)) == False and selectedIndexes[0].row() - 1 > currentPlaylistIndex:
            # Get the first and maximum index rows
            firstIndex = selectedIndexes[0].row()
            maxIndex = selectedIndexes[len(selectedIndexes) - 1].row()

            # Get selected media
            media = self.getSelectedMedia(firstIndex, maxIndex)
            
            # Set the previous selected indexes
            previousSelectedIndexes = self.playlistView.selectedIndexes()
            
            # Insert all of the media in the list to 1 indexes before the current on the playlist, remove the previous original media instances (+1 to first and maximum) from the playlist and emit the playlist model layout change signal
            self.playlist.insertMedia(firstIndex - 1, media)
            self.playlist.removeMedia(firstIndex + 1, maxIndex + 1)
            self.playlistModel.layoutChanged.emit()

            # On the playlist view selection model, call the select function with the selection model deselect parameter to deselect all of the items in the previus selected indexes
            len_previousSelectedIndexes = len(previousSelectedIndexes)
            self.playlistViewSelectionModel.select(QtCore.QItemSelection(previousSelectedIndexes[0], previousSelectedIndexes[len_previousSelectedIndexes - 1]), QtCore.QItemSelectionModel.Deselect)

            # On the playlist view selection model, call the select function with the selection model select parameter to select all of the moved selected indexes (all of the previous selected indexes shifted by 1 before)
            self.playlistViewSelectionModel.select(QtCore.QItemSelection(self.playlistModel.index(previousSelectedIndexes[0].row() - 1), self.playlistModel.index(previousSelectedIndexes[len_previousSelectedIndexes - 1].row() - 1)), QtCore.QItemSelectionModel.Select)

    def getSelectedMedia(self, firstIndex: int, maxIndex: int):
        # Append all selected media + 1 from playlist to a QMediaContent list
        media: List[QtMultimedia.QMediaContent] = []
        for i in range(firstIndex, maxIndex + 1):
            media.append(self.playlist.media(i))
        
        return media

    def playlist_clear(self):
        # Clear the playlist, clear the media config log and emit the playlist model layout changed signal
        self.playlist.clear()
        lib.clearConfigFile(lib.configDir, lib.mediaFileName)
        self.playlistModel.layoutChanged.emit()
    
    #
    #   Revise
    #

    def playlist_position_changed(self, index: QtCore.QModelIndex):
        # Set playlist current index from index
        self.playlist.setCurrentIndex(index)

    def playlist_selection_changed(self, selection: QtCore.QItemSelection):
        #
        #   Deprecated
        #

        # If selection indexes are passed, set index to the first row from the index array
        if len(selection.indexes()) > 0:
            index = selection.indexes()[0].row()

            # If index is not negative, (deselection), set playlist view current index to model index from local index
            if index > -1:
                self.playlistView.setCurrentIndex(self.playlistModel.index(index))

    def init_playpause(self):
        # Initialise the play/pause button with text/icon and signal connection
        self.control_playpause.setText(self.tr("Play"))
        self.control_playpause.pressed.connect(self.play)

    def pause(self):
        # Call the pause method of the player and replace play/pause button properties to play; disconnect, set icon and connect to play method
        self.player.pause()
        self.control_playpause.pressed.disconnect()
        self.control_playpause.setText("Play")
        self.control_playpause.pressed.connect(self.play)
    
    def play(self):
        # If playlist has media, call the play method of the player and replace play/pause button properties to pause; disconnect, set icon and connect to pause method
        if self.playlist.mediaCount() > 0:
            self.player.play()
            self.control_playpause.pressed.disconnect()
            self.control_playpause.setText(self.tr("Pause"))
            self.control_playpause.pressed.connect(self.pause)

    def playpause(self):
        # If not playing, playing, otherwise pause
        if self.isPlaying():
            self.pause()
        else:
            self.play()

    #
    #   Revise
    #

    def update_metadata(self, media: QtMultimedia.QMediaContent):
        # Todo: if no media is playing, hide the metadata, otherwise set the metadata from the metadata class and set the label text
        if media.isNull():
            self.metadata_label.hide()
        else:
            mediaPath = lib.urlStringToPath(media.canonicalUrl().toString())

            if getattr(self, "metadata_separator", None) == None:
                self.metadata_separator = " - "

            mutagen_metadata = mutagen.File(mediaPath)
            self.metadata = lib.Metadata(mutagen_metadata)

            if self.metadata.title and self.metadata.album:
                metadata_string = self.metadata.title + self.metadata_separator + self.metadata.album
            else:
                metadata_string = media.canonicalUrl().fileName()

            self.metadata_label.setText(metadata_string)
            self.metadata_label.show()

    def update_coverart(self, media: QtMultimedia.QMediaContent):
        # If no media is playing, hide the cover art, otherwise separate the url string into a path, set the label pixmap and show
        if media.isNull():
            self.coverart_label.hide()
        else:
            mediaPath = lib.urlStringToPath(media.canonicalUrl().toString())
            coverart_pixmap = lib.get_coverart_pixmap_from_metadata(mutagen.File(mediaPath))

            if coverart_pixmap == None:
                coverart_path = lib.get_coverart(os.path.dirname(mediaPath))
                if coverart_path:
                    coverart_pixmap = QtGui.QPixmap()
                    coverart_pixmap.load(coverart_path)

            if coverart_pixmap:
                self.coverart_label.setPixmap(coverart_pixmap.scaledToWidth(self.coverart_width))
                self.coverart_label.show()
            else:
                self.coverart_label.hide()

    def update_media(self, media: QtMultimedia.QMediaContent):
        # If playing, update the play/pause button to the playing state, otherwise set its properties to the paused state
        self.updatePlayingState()
        
        # Called on media change, update track metadata and cover art
        self.update_metadata(media)
        self.update_coverart(media)

    def connect_update_media(self):
        # Connect cover art update method to playlist current media changed signal
        self.playlist.currentMediaChanged.connect(self.update_media)

    def createLayout(self):
        # Create main vertical layout, add horizontal layouts with added sub-widgets to vertical layout
        detailsGroup = QtWidgets.QGroupBox()
        hControlLayout = QtWidgets.QHBoxLayout()
        hControlLayout.addWidget(self.control_previous)
        hControlLayout.addWidget(self.control_playpause)
        hControlLayout.addWidget(self.control_next)
        hControlLayout.addWidget(self.volumeSlider)

        hTimeLayout = QtWidgets.QHBoxLayout()
        hTimeLayout.addWidget(self.timePositionLabel)
        hTimeLayout.addWidget(self.timeSlider)
        hTimeLayout.addWidget(self.totalTimeLabel)

        vDetailsLayout = QtWidgets.QVBoxLayout()
        vDetailsLayout.addLayout(hControlLayout)
        vDetailsLayout.addLayout(hTimeLayout)
        vDetailsLayout.addWidget(self.metadata_label)

        hDetailsLayout = QtWidgets.QHBoxLayout()
        hDetailsLayout.addLayout(vDetailsLayout)
        hDetailsLayout.addWidget(self.coverart_label)

        detailsGroup.setLayout(hDetailsLayout)

        actionsLayout = QtWidgets.QHBoxLayout()
        actionsLayout.addWidget(self.control_playlist_moveDown)
        actionsLayout.addWidget(self.control_playlist_moveUp)
        actionsLayout.addWidget(self.control_playlist_remove)
        actionsLayout.addWidget(self.control_playlist_clear)

        self.vLayout = QtWidgets.QVBoxLayout()
        self.vLayout.addWidget(detailsGroup)
        self.vLayout.addLayout(actionsLayout)
        self.vLayout.addWidget(self.playlistView)

    def createCentralWidget(self):
        # Create central widget, call set central widget method and set widget layout
        self.centralWidget = QtWidgets.QWidget()
        self.setCentralWidget(self.centralWidget)
        self.centralWidget.setLayout(self.vLayout)

    def createMenus(self):
        # Create main menu from menuBar method, use addMenu for submenus and add QActions accordingly with triggered connect method, set shortcut from QKeySequence on QActions
        self.mainMenu = self.menuBar()
        fileMenu = self.mainMenu.addMenu(self.tr("File"))
        playlistMenu = self.mainMenu.addMenu(self.tr("Playlist"))

        closeAction = QtWidgets.QAction(self.tr("Close Window"), self)
        closeAction.triggered.connect(self.closeWindow)
        closeAction.setShortcut(QtGui.QKeySequence(self.tr("Ctrl+W", "File|Close Window")))

        preferencesAction = QtWidgets.QAction(self.tr("Preferences"), self)
        preferencesAction.triggered.connect(self.showPreferences)
        preferencesAction.setShortcut(QtGui.QKeySequence(self.tr("Ctrl+,", "File|Preferences")))

        openFileAction = QtWidgets.QAction(self.tr("Open File"), self)
        openFileAction.triggered.connect(self.open_files)
        openFileAction.setShortcut(QtGui.QKeySequence(self.tr("Ctrl+O", "File|Open")))

        openDirAction = QtWidgets.QAction(self.tr("Open Directory"), self)
        openDirAction.triggered.connect(self.open_directory)
        openDirAction.setShortcut(QtGui.QKeySequence(self.tr("Ctrl+Shift+O", "File|Open Directory")))

        playlistRemoveAction = QtWidgets.QAction(self.tr("Remove"), self)
        playlistRemoveAction.triggered.connect(self.removeMedia)

        playlistClearAction = QtWidgets.QAction(self.tr("Clear"), self)
        playlistClearAction.triggered.connect(self.playlist_clear)
        playlistClearAction.setShortcut(QtGui.QKeySequence(self.tr("Ctrl+Backspace", "Playlist|Clear")))

        fileMenu.addAction(closeAction)
        fileMenu.addAction(preferencesAction)
        fileMenu.addAction(openFileAction)
        fileMenu.addAction(openDirAction)
        playlistMenu.addAction(playlistRemoveAction)
        playlistMenu.addAction(playlistClearAction)

    def closeWindow(self):
        # Get the active window from the QApplication, quit the application if the active window is the player, otherwise hide and then destroy that window
        activeWindow = self.app.activeWindow()

        if activeWindow == self:
            self.app.quit()
        else:
            # Note: the widget must be hidden before destruction, otherwise a segmentation fault can occur when quitting the application
            activeWindow.hide()
            activeWindow.destroy()

    def showPreferences(self):
        # Create instance of Preferences widget with the QApplication given as a parameter
        self.preferencesView = Preferences(self.app)

    def open_files(self):
        # Set last media count for playlist media check later on
        self.lastMediaCount = self.playlist.mediaCount()
        
        # Set paths from QFileDialog getOpenFileNames, filetypes formatted as "Name (*.extension);;Name" etc.
        paths, _ = QtWidgets.QFileDialog.getOpenFileNames(self, self.tr("Open File"), "", self.tr("All Files (*.*);;Waveform Audio (*.wav);;mp3 Audio (*.mp3)"))

        # For each path, add media QMediaContent from local file to playlist if the filetype is supported
        if paths:
            for path in paths:
                if self.isSupportedFileFormat(path):
                    self.addMediaFromFile(path)
            
            # Emit playlist model layout change and play if paused
            self.playlistModel.layoutChanged.emit()

            # Check new media and play if conditions are met
            self.playNewMedia()

            # Write media to config
            self.writeMediaToConfig()

    def isSupportedFileFormat(self, path: str) -> bool:
        # Split the path by the extension separator and if the list of supported formats contains the last element of the list, return true
        split = path.split(os.path.extsep)

        if lib.supportedFormats.__contains__(split[len(split)-1]):
            return True
        else:
            return False

    def open_directory(self):
        # Set last media count for playlist media check later on
        self.lastMediaCount = self.playlist.mediaCount()

        # Set directory from QFileDialog getExistingDirectory
        dirPath = QtWidgets.QFileDialog.getExistingDirectory(self, self.tr("Open Folder"), "")

        # If a path was returned, get a directory listing, sort it and for every file in the list get the full path: if the format is supported, add the media to the playlist
        if dirPath:
            dirList = os.listdir(dirPath)
            dirList.sort()
            
            for fname in dirList:
                path = os.path.join(dirPath, fname)
                
                if self.isSupportedFileFormat(path):
                    self.addMediaFromFile(path)

            # Emit playlist model layout change and play if paused
            self.playlistModel.layoutChanged.emit()

            # Check new media and play if conditions are met
            self.playNewMedia()

            # Write media to config
            self.writeMediaToConfig()

    def addMediaFromFile(self, path: str):
        # Add the media to the playlist with a QMediaContent instance from the local file
        self.playlist.addMedia(
            QtMultimedia.QMediaContent(QtCore.QUrl.fromLocalFile(path))
        )

    def addMediaFromConfig(self):
        # If the file exists, read in each line of the media log to a list and add the media content from each path to the playlist
        paths: List[str] = []
        mediaLog = os.path.join(lib.configDir, lib.mediaFileName)

        if os.path.isfile(mediaLog):
            with open(mediaLog, "r") as mediaData:
                paths = mediaData.read().split("\n")

            for path in paths:
                if path != "":
                    self.playlist.addMedia(
                        QtMultimedia.QMediaContent(QtCore.QUrl.fromLocalFile(path))
                    )

    def writeMediaToConfig(self):
        # Add path from canonical url string of each media item in the playlist to a list and write it to the config
        paths: List[str] = []
        for i in range(self.playlist.mediaCount()):
            urlString = self.playlist.media(i).canonicalUrl().toString()
            paths.append(lib.urlStringToPath(urlString))
        
        lib.writeToConfig(lib.configDir, lib.mediaFileName, paths)

    def isPlaying(self) -> bool:
        if self.player.state() == QtMultimedia.QMediaPlayer.PlayingState:
            return True
        else:
            return False

    #
    #   Revise
    #

    def removeMedia(self):
        selectedIndexes = self.playlistView.selectedIndexes()
        if len(selectedIndexes) > 0:
            for index in selectedIndexes:
                self.playlist.removeMedia(index.row(), selectedIndexes[len(selectedIndexes)-1].row())
                self.playlistModel.layoutChanged.emit()

    def createShortcuts(self):
        # Create QShortcuts from QKeySequences with the shortcut and menu item passed as arguments
        shortcut_playpause_space = QtWidgets.QShortcut(QtGui.QKeySequence(self.tr("Space")), self)
        shortcut_playpause = QtWidgets.QShortcut(QtGui.QKeySequence(QtCore.Qt.Key_MediaPlay), self)
        shortcut_playpause_space.activated.connect(self.playpause)
        shortcut_playpause.activated.connect(self.playpause)

        shortcut_delete = QtWidgets.QShortcut(QtGui.QKeySequence(self.tr("Backspace")), self)
        shortcut_delete.activated.connect(self.removeMedia)

        shortcut_previous = QtWidgets.QShortcut(QtGui.QKeySequence(QtCore.Qt.Key_MediaLast), self)
        shortcut_previous.activated.connect(self.playlist.previous)

        shortcut_next = QtWidgets.QShortcut(QtGui.QKeySequence(QtCore.Qt.Key_MediaNext), self)
        shortcut_next.activated.connect(self.playlist.next)

        if is_admin:
            keyboard.add_hotkey(0x83, self.playpause)

    #
    #   Revise
    #
    #   Synopsis of drag and drop:
    #       - Set accept drops to true
    #   dragEnterEvent (QDragEnterEvent):
    #       -   Call event accept proposed action method if event mime data has urls
    #   dropEvent (QDropEvent):
    #       -   Set last media count
    #       -   If a url is a directory, append paths from os.listdir of supported files to a list
    #           - Sort the list and add urls from the paths
    #       -   Add media to playlist from urls
    #       -   Emit model layout change
    #       -   Call playNewMedia:
    #           - If not playing and last media count was 0, play
    #       -   Write media to config
    #

    def dragEnterEvent(self, event: QtGui.QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QtGui.QDropEvent):
        self.lastMediaCount = self.playlist.mediaCount()
        
        for url in event.mimeData().urls():
            path = lib.urlStringToPath(url.toString())

            if os.path.isdir(path):
                paths: List[str] = []

                for fname in os.listdir(path):
                    split = fname.split(os.path.extsep)

                    if lib.supportedFormats.__contains__(split[len(split)-1]):
                        paths.append(path + fname)
                
                if paths:
                    paths.sort()
                    for path in paths:
                        self.playlist.addMedia(
                            QtMultimedia.QMediaContent(QtCore.QUrl.fromLocalFile(path))
                        )
            else:
                split = url.toString().split(os.path.extsep)

                if lib.supportedFormats.__contains__(split[len(split)-1]):
                    self.playlist.addMedia(
                            QtMultimedia.QMediaContent(url)
                    )

        self.playlistModel.layoutChanged.emit()
        self.playNewMedia()
        self.writeMediaToConfig()

    def playNewMedia(self):
        # Play if not playing and the last media count is not 0
        if self.isPlaying() == False and self.lastMediaCount == 0:
            self.play()

    def switchMedia(self):
        # Get selected indexes from playlist view, if there are indexes selected, set the new current playlist index and play the new media
        selectedIndexes = self.playlistView.selectedIndexes()
        if len(selectedIndexes) > 0:
            self.playlist.setCurrentIndex(selectedIndexes[0].row())
            self.playNewMedia()

#
#   Todo: complete, comment and revise
#

class Preferences(QtWidgets.QWidget):
    def __init__(self, app: QtWidgets.QApplication):
        super().__init__()
        self.left = 0
        self.top = 0
        self.width = 0
        self.height = 0
        self.title = lib.progName + lib.titleSeparator + self.tr("Preferences")
        self.app = app

        self.initUI()

    def initUI(self):
        self.setGeometry(self.left, self.top, self.width, self.height)
        self.setWindowTitle(self.title)
        self.createWidgets()
        self.createLayout()

        self.show()

    def createWidgets(self):
        self.styleLabel = QtWidgets.QLabel(self.tr("Style"), self)
        self.styleBox = QtWidgets.QComboBox(self)
        
        for style in lib.styles:
            self.styleBox.addItem(self.tr(style.name))
        
        self.styleBox.currentIndexChanged.connect(self.styleSelectionChanged)

    def createLayout(self):
        layout = QtWidgets.QGridLayout(self)
        layout.addWidget(self.styleLabel, 0, 0)
        layout.addWidget(self.styleBox, 0, 1)
        self.setLayout(layout)

    def styleSelectionChanged(self, index: int):
        lib.globalStyleSheet = lib.styles[index].styleSheet
        self.app.setStyleSheet(lib.globalStyleSheet)