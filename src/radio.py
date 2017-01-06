#! /usr/bin/env python
# -*- coding: utf-8 -*-
"""Radio state and control.

We do not control the radio directly. Intead we integrate with an 
echolink/IRLP node. State is determined by a combination of running external 
binaries and checking for the existence of files. Control is achieved by 
executing external binaries and shell scripts.
"""

import os
import subprocess
import sys

class Radio(object):
    """An IRLP node installation that we can query and control.
    
    Pass in the root directory of the installation. For example if the IRLP 
    installation is in these directories:
        /home/user/irlp/bin
        /home/user/irlp/local
        /home/user/irlp/scripts
    ... you would pass in '/home/user/irlp'
    """
    
    def __init__(self, root_path):
        if not os.path.isdir(root_path):
            raise ValueError("Supplied path is not directory: %s" % root_path)
        self._root = root_path
        self._ptt_lock = False
        self._channel_clear = False
        self._clear_count = 0
        self._enable_dtmf()
    
    # Public
    
    # Querying state
    
    def ptt_active(self):
        try:
            return self._run_bin("pttstate") == 1
        except:
            return True
    
    def channel_active(self):
        try:
            return self._run_bin("cosstate") == 1
        except:
            return True
    
    def channel_clear(self):
        return (not self.channel_active()) and self._channel_clear
    
    def echolink_active(self):
        check_path = os.path.join(self._root, "local", "echo_enable")
        return os.path.isfile(check_path)
    
    def irlp_active(self):
        check_path = os.path.join(self._root, "local", "enable")
        return os.path.isfile(check_path)
    
    def ptt_locked_out(self):
        return self._ptt_lock
    
    # Manipulating controls
    
    def ptt_on(self):
        print("PTT ON")
        self._disable_dtmf()
        if (not self.ptt_locked_out()) and self.channel_clear():
            self._run_bin("key")
            return True
        else:
            return False
    
    def ptt_off(self):
        print("PTT OFF")
        self._enable_dtmf()
        self._run_bin("unkey")
    
    def irlp_on(self):
        print("IRLP ON")
        self._run_script("enable")
    
    def irlp_off(self):
        print("IRLP OFF")
        self._run_script("disable")
    
    def echolink_on(self):
        print("ECHOLINK ON")
        self._run_echo_script("echo_enable")
    
    def echolink_off(self):
        print("ECHOLINK OFF")
        self._run_echo_script("echo_disable")
    
    def ptt_lock(self):
        self._ptt_lock = True
        if self.ptt_active():
            self.ptt_off()
    
    def ptt_unlock(self):
        self._ptt_lock = False
    
    def tick(self):
        """Called every 250ms by main app to get work done."""
        
        if self.channel_active():
            self._clear_count = 0
        else:
            self._clear_count += 1
        
        # Need to be clear for at least two seconds before we jump in
        self._channel_clear = (self._clear_count > 8)

    
    # Private
    
    def _run_bin(self, command):
        bin_path = os.path.join(self._root, "bin", command)
        return subprocess.call([bin_path])
    
    def _run_script(self, command):
        script_path = os.path.join(self._root, "scripts", command)
        return subprocess.call([script_path])

    def _run_echo_script(self, command):
        script_path = os.path.join(self._root, "features", "EchoIRLP", "scripts", command)
        return subprocess.call([script_path])

    def _disable_dtmf(self):
        # This daemon will shut off PTT if it detects a transmission going for longer than 5 mins
        subprocess.call(["killall", "dtmf"])
    
    def _enable_dtmf(self):
        # Enable DTMF listening again
        # The process can run multiple times so make sure it isn't already running
        if not "dtmf" in subprocess.check_output(["ps", "waux"]):
            dtmf_path = os.path.join(self._root, "bin", "dtmf")
            subprocess.call([dtmf_path])
