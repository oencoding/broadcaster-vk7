#! /usr/bin/env python
# -*- coding: utf-8 -*-
"""Audio file playback and management
"""

from datetime import datetime, timedelta
import os
import sys
import time
import uuid
import pickle
from threading import Timer

import playback

class Gap(object):
    """A playlist item that represents a pause between other items.

    The node is clear of the channel while the gap proceeds.
    """

    def __init__(self, duration):
        self.duration = duration

    def __str__(self):
        return "%.1f second gap" % self.duration


class Inet(object):
    """A playlist item that represents turning echolink and IRLP on or off.
    """

    def __init__(self, on):
        self.on = on

    def __str__(self):
        text = "on" if self.on else "off"
        return "IRLP/Echolink %s" % text


class ScheduledItem(object):
    def __init__(self):
        self.identifier = str(uuid.uuid4())
        self.playlist = []
        self.position = 0
        self.start_time = datetime.now()
        self.pending = False


class Scheduler(object):

    schedule_file = "../config/schedule.dat"

    def __init__(self, player, radio):
        self._player = player
        self._radio = radio
        self._items = []

        if os.path.isfile(self.schedule_file):
            f = open(self.schedule_file, "rb")
            self._items = pickle.load(f)
            f.close()

    def save_items(self):
        # Make sure it exists first
        #open(self.schedule_file, 'a').close()
        f = open(self.schedule_file, "wb")
        pickle.dump(self._items, f)
        f.close()

    def add_new_schedule(self, json_dict):
        item = ScheduledItem()
        for f in json_dict["playlist"]:
            if f.startswith(":GAP:"):
                seconds = 0
                try:
                    seconds = int(f[5:])
                except ValueError:
                    seconds = 5 # sensible default
                gap = Gap(seconds)
                item.playlist.append(gap)
            elif f.startswith(":INETON:"):
                item.playlist.append(Inet(True))
            elif f.startswith(":INETOFF:"):
                item.playlist.append(Inet(False))
            else:
                a = playback.AudioFile("../files/%s" % f)
                item.playlist.append(a)
        timestamp = json_dict["date"] + " " + json_dict["time"]
        date = datetime.strptime(timestamp, "%d/%m/%Y %I:%M:%S %p")
        item.start_time = date
        # If it was scheduled in the past, do not mark it pending
        item.pending = datetime.now() < item.start_time
        self._items.append(item)
        self.save_items()

    def delete_schedule(self, identifier):
        self._items = [i for i in self._items if i.identifier != identifier]
        self.save_items()

    def tick(self):
        for i in self._items:
            if i.pending and i.start_time < datetime.now() \
                    and len(i.playlist) > 0:
                # Uh make this better
                i.pending = False
                self.save_items()
                self.current_item = i
                self.current_item.position = 0
                self._play_playlist_entry(0)

    def playback_finished(self):
        # The player is letting us know that it finished playing a file
        self.current_item.position += 1
        if self.current_item.position < len(self.current_item.playlist):
            self._play_playlist_entry(self.current_item.position)
        else:
            self.current_item = None

    def _play_playlist_entry(self, position):
        entry = self.current_item.playlist[position]
        if isinstance(entry, Gap):
            print("Gap of duration %d" % entry.duration)
            Timer(entry.duration, self.playback_finished, ()).start()
        elif isinstance(entry, Inet):
            if entry.on:
                print("Echolink and IRLP on")
                self._radio.echolink_on()
                self._radio.irlp_on()
            else:
                print("Echolink and IRLP off")
                self._radio.echolink_off()
                self._radio.irlp_off()
            self.playback_finished()
        else:
            print("Playing entry in position %d" % position)
            # Wait one second to let PTT reset
            Timer(1.0, self._player.play_file, (entry, self.playback_finished)).start()
