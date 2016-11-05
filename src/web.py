#! /usr/bin/env python
# -*- coding: utf-8 -*-
"""Twisted web controllers.

Various classes to handle different parts of the URL tree.
"""

import cgi
import json
import scheduler

from twisted.web import server, resource
from twisted.web.template import Element, XMLFile
from twisted.python.filepath import FilePath
from twisted.web.template import flattenString

import os


class RadioController(resource.Resource):
    isLeaf = False
    
    def __init__(self, services):
        resource.Resource.__init__(self)
        self.putChild("status", RadioStatus(services))
        self.putChild("stop", RadioStop(services))
        self.putChild("enable_irlp", RadioEnableIRLP(services))
        self.putChild("disable_irlp", RadioDisableIRLP(services))
        self.putChild("enable_echolink", RadioEnableEcholink(services))
        self.putChild("disable_echolink", RadioDisableEcholink(services))
        
    def render_GET(self, request):
        return ""

    
# Abstract
class RadioLeaf(resource.Resource):
    isLeaf = True
    def __init__(self, services):
        self._s = services
        
        
class RadioStatus(RadioLeaf):
    def render_GET(self, request):
        status = {}
        
        status["ptt"] = self._s.radio.ptt_active()
        status["ptt_locked"] = self._s.radio.ptt_locked_out()
        status["irlp_active"] = self._s.radio.irlp_active()
        status["echolink_active"] = self._s.radio.echolink_active()
        
        status["file_playing"] = self._s.player.current_file()
        status["playback_status"] = self._s.player.playback_status()
        status["progress"] = self._s.player.progress_string()
        
        return json.dumps(status, sort_keys=True, indent=4)
    

class RadioStop(RadioLeaf):
    def render_POST(self, request):
        print("Stopping radio...")
        if self._s.player.playback_status() == "playing":
            self._s.player.stop()
        else:
            # Allow user to override IRLP/echolink
            self._s.radio.ptt_off()
        return ""

class RadioEnableIRLP(RadioLeaf):
    def render_POST(self, request):
        self._s.radio.irlp_on()
        return ""
    
class RadioDisableIRLP(RadioLeaf):
    def render_POST(self, request):
        self._s.radio.irlp_off()
        return ""
    
class RadioEnableEcholink(RadioLeaf):
    def render_POST(self, request):
        self._s.radio.echolink_on()
        return ""

class RadioDisableEcholink(RadioLeaf):
    def render_POST(self, request):
        self._s.radio.echolink_off()
        return ""

class HomePageTemplate(Element):
    loader = XMLFile(FilePath('../templates/home.xml'))
        

class HomePage(resource.Resource):
    isLeaf = True
    def render_GET(self, request):
        def renderDone(output):
            request.write(output)
            request.finish()
        flattenString(None, HomePageTemplate()).addCallback(renderDone)
        return server.NOT_DONE_YET



class ScheduleController(resource.Resource):
    isLeaf = False
    
    def __init__(self, services):
        resource.Resource.__init__(self)
        self.putChild("files", ScheduleFiles(services))
        self.putChild("new", ScheduleNew(services))
        self.putChild("list", ScheduleList(services))
        self.putChild("delete", ScheduleDelete(services))
        
    def render_GET(self, request):
        return ""

    
class ScheduleLeaf(resource.Resource):
    isLeaf = True
    def __init__(self, services):
        self._s = services
        
class ScheduleFiles(ScheduleLeaf):
    def render_GET(self, request):
        files = os.listdir('../files/')
        return json.dumps(files, sort_keys=True, indent=4)

class ScheduleNew(ScheduleLeaf):
    def render_POST(self, request):
        new_json = request.content.read()
        d = json.loads(new_json)
        self._s.scheduler.add_new_schedule(d)
        return ""
        
class ScheduleList(ScheduleLeaf):
    def render_GET(self, request):
        items = self._s.scheduler._items
        s_list = []
        for i in items:
            s_item = {}
            s_item["identifier"] = i.identifier
            s_item["playlist"] = [str(e) for e in i.playlist]
            s_item["timestamp_string"] = i.start_time.strftime("%I:%M %p %d/%m/%Y")
            s_list.append(s_item)
        return json.dumps(s_list, sort_keys=True, indent=4)
    
class ScheduleDelete(ScheduleLeaf):
    def render_POST(self, request):
        identifier = request.content.read()
        print("Deleting id %s" % identifier)
        self._s.scheduler.delete_schedule(identifier)
        return ""
