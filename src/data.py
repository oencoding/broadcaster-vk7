#! /usr/bin/env python
# -*- coding: utf-8 -*-
"""Management of data files such as WAVE and MP3 files on disk
"""

import os
import sys

class DataManager(object):

    def __init__(self, path):
        self._path = path

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
                seconds = int(f[5:])
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
        date = datetime.strptime(timestamp, "%d/%m/%Y %I:%M %p")
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
