#!/usr/bin/python

from twisted.web import server, resource, static
from twisted.internet import reactor, task
from twisted.web.wsgi import WSGIResource

from twisted.web.template import Element, renderer, XMLFile
from twisted.python.filepath import FilePath
from twisted.web.template import flattenString

import os

from wsgidav.wsgidav_app import WsgiDAVApp
from wsgidav.fs_dav_provider import FilesystemProvider
from wsgidav.wsgidav_app import DEFAULT_CONFIG

from configobj import ConfigObj

import radio
import playback
import web
import scheduler

app_settings = ConfigObj("../config/settings.cfg")
irlp_home = app_settings['irlp_home']
port = int(app_settings['port'])


class ExampleElement(Element):
    loader = XMLFile(FilePath('../web/index.xml'))

    def getFiles(self):
        return os.listdir('../files/')

    @renderer
    def files(self, request, tag):
        for f in self.getFiles():
            yield tag.clone().fillSlots(filename=f, path="../files/" + f)




class Simple(resource.Resource):
    isLeaf = False
    def render_GET(self, request):
        def renderDone(output):
            request.write(output)
            request.finish()
        flattenString(None, ExampleElement()).addCallback(renderDone)
        return server.NOT_DONE_YET

class Hello(resource.Resource):
    isLeaf = True
    def render_GET(self, request):
        #request.write("Hello, world\n")
        p = request.URLPath()
        print(p)
        print(p.here())
        #print(p.child())
        print(p.parent())
        #print(p.sibling())
        print(p.path)
        print(p.query)
        return "Hello, world\n"

config = DEFAULT_CONFIG.copy()
provider = FilesystemProvider('../files/')
config.update({
    "mount_path": "",
    "provider_mapping": {"/": provider},
    "user_mapping": {},
    "verbose": 1,
    "enable_loggers": [],
    "propsmanager": True,      # True: use property_manager.PropertyManager
    "locksmanager": True,      # True: use lock_manager.LockManager
    "domaincontroller": None,  # None: domain_controller.WsgiDAVDomainController(user_mapping)
})
wsgidav = WsgiDAVApp(config)
def wsgidav_application(environ, start_response):
    return wsgidav(environ, start_response)

class Services:
    pass

services = Services()
services.radio = radio.Radio(irlp_home)
services.player = playback.Player(services.radio)
services.scheduler = scheduler.Scheduler(services.player, services.radio)

# Put all top level module instances here that need to get stuff done
def top_ticker():
    services.radio.tick()
    services.player.tick()
    services.scheduler.tick()



root = static.Data("", "text/plain")
root.putChild("files", static.File("../files"))
root.putChild("static", static.File("../static"))
#simple = Simple()
#simple.putChild("hello", Hello())
#root.putChild("api", simple)
radio_controller = web.RadioController(services)
root.putChild("radio", radio_controller)
schedule_controller = web.ScheduleController(services)
root.putChild("schedule", schedule_controller)
root.putChild("dav", WSGIResource(reactor, reactor.getThreadPool(), wsgidav_application))
root.putChild("home", web.HomePage())

site = server.Site(root)




ticker = task.LoopingCall(top_ticker)
ticker.start(0.250) # call every 250 ms

reactor.listenTCP(port, site)
reactor.run()
