#! /usr/bin/env python
# -*- coding: utf-8 -*-
"""Audio file playback and management
"""

import contextlib
from datetime import datetime
import math
import os
import subprocess
import sys
import wave
import mad
import time

class AudioFile(object):
    """An audio file on disk.

    Initialise it with a path. It will analyse the contents of the file and be
    able to report its file format and duration.

    Currently only works with PCM WAVE files.
    """

    def __init__(self, path):
        if not os.path.isfile(path):
            raise ValueError("Not an audio file path: %s" % path)
        self._path = path

    def __str__(self):
        return self.filename()

    def _extension(self):
        filename, ext = os.path.splitext(self.filename())
        return ext

    def file_format(self):
        """Returns a string describing the file format."""
        ext = self._extension().upper()
        if ext == ".WAV":
            return "WAVE"
        elif self._extension().upper() == ".MP3":
            return "MP3"
        return "unsupported"

    def is_supported(self):
        return self.file_format() != "unsupported"

    def is_mp3(self):
        return self.file_format() == "MP3"

    def is_wave(self):
        return self.file_format() == "WAVE"

    def duration(self):
        """Returns the file duration in floating point seconds."""
        try:
            if self.is_wave():
                with contextlib.closing(wave.open(self._path)) as f:
                    frames = f.getnframes()
                    rate = f.getframerate()
                    duration = frames / float(rate)
                    return duration
            elif self.is_mp3():
                mf = mad.MadFile(self._path)
                ms = mf.total_time()
                return ms / 1000.0
        except:
            pass
        return 0.0

    def duration_string(self):
        """Returns the file duration in the format MM:SS.SS"""
        seconds = self.duration()
        minutes = int(seconds / 60)
        remaining_seconds = seconds - (minutes*60)
        return "%02d:%05.2f" % (minutes, remaining_seconds)

    def filename(self):
        """Returns the base filename of the object, e.g. 'news.wav'"""
        return os.path.basename(self._path)

    def path(self):
        """Returns full path to audio file"""
        return self._path

    def size(self):
        """Returns the size of the file in bytes."""
        return os.path.getsize(self._path)

    def size_string_mb(self):
        """Returns the size of the tile in the format 'XXX.XX MB'"""
        size_bytes = self.size()
        return "%.2f MB" % (float(size_bytes) / 1024 / 1024)

class Player(object):

    def __init__(self, radio):
        self._radio = radio
        self._playing_now = False
        self._attempting_to_play = False
        self._playing_process = None
        self._playing_audio = None

    def play_file(self, audio_file, finished_callback):
        self._finished_callback = finished_callback
        if self._playing_now:
            # We already have PTT, just switch files
            self._stop_audio()
            self._playing_audio = audio_file
            self._start_audio()
        else:
            # We'll confirm that the channel is clear and play in tick()
            self._playing_audio = audio_file
            self._attempting_to_play = True

    def stop(self):
        if self._playing_now:
            self._stop_audio()
            self._radio.ptt_off()
            self._playing_now = False
        self._playing_audio = None
        self._attempting_to_play = False
        self._finished_callback = False

    def playback_status(self):
        if self._attempting_to_play:
            return "waiting_to_clear"
        if self._playing_now:
            return "playing"
        return "stopped"

    def current_file(self):
        if self._playing_audio == None:
            return "-"
        return self._playing_audio.filename()

    def seconds_played(self):
        if not self._playing_now:
            return 0.0
        return (datetime.now() - self._start_time).total_seconds()

    def seconds_duration(self):
        if self._playing_audio == None:
            return 0.0
        return self._playing_audio.duration()

    def progress_string(self):
        # Returns "MM:SS / MM:SS"
        played = self.seconds_played()
        duration = self.seconds_duration()
        mins_played = int(played / 60)
        secs_played = played - (mins_played * 60)
        mins_duration = int(duration / 60)
        secs_duration = duration - (mins_duration * 60)
        return "%02d:%02d / %02d:%02d" \
            % (mins_played, secs_played, mins_duration, secs_duration)

    def _start_audio(self):
        self._playing_now = True
        self._start_time = datetime.now()
        # Give the repeater a moment to key up
        time.sleep(0.5)
        if self._playing_audio.is_mp3():
            self._playing_process = subprocess.Popen(
                ["mpg123", "-m", "-s", "-r", "44100", self._playing_audio.path()],
                stdout=subprocess.PIPE)
            p2 = subprocess.Popen("play --buffer 2048 -t raw -e signed-integer -r 44100 -b 16 -c 1 - compand 0.1,0.3 -60,-60,-30,-20,-20,-15,-4,-8,-2,-7 -2".split(),
                stdin=self._playing_process.stdout, stdout=subprocess.PIPE)
            self._playing_process.stdout.close()
        else: # at least attempt as wave
            self._playing_process = subprocess.Popen(
                ['play', '--buffer', '2048', self._playing_audio.path()] + "compand 0.1,0.3 -60,-60,-30,-20,-20,-15,-4,-8,-2,-7 -2".split())

    def _stop_audio(self):
        if self._playing_process != None:
            self._playing_process.terminate()
            self._playing_process.wait()
            self._playing_process = None

    def tick(self):
        if self._playing_now and self._playing_process != None:
            if self._playing_process.poll() != None:
                print("naturally finished")
                # Finished playing naturally
                self._playing_process = None
                if self._finished_callback != None:
                    self._finished_callback()
                self.stop()
        else:
            if self._attempting_to_play and self._radio.channel_clear():
                print("channel clear, starting playback")
                self._attempting_to_play = False
                self._radio.ptt_on() #TODO check return value
                self._start_audio()
