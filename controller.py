#!/usr/bin/python3

import argparse
import asyncio
import functools
import logging
import signal

import aiohttp
from aiortc import RTCPeerConnection, RTCSessionDescription, VideoStreamTrack
from aiortc.contrib.media import MediaPlayer

import socketio


class SignalingSession(socketio.AsyncClientNamespace):
    def __init__(self, url, controller):
        socketio.AsyncClientNamespace.__init__(self)
        self._sio = None
        self._url = url
        self._controller = controller

    async def create(self):
        self._sio = socketio.AsyncClient()
        self._sio.register_namespace(self)
        await self._sio.connect(self._url)
    
    async def attach(self, room):
        await self._sio.emit('join as robot', room)
    
    async def sendMessage(self, message):
        await self._sio.send(message)
    
    
    async def on_joined(self, room, socketId):
        print("Joined room {} with id {}".format(room, socketId))
    
    async def on_log(self, data):
        print(' '.join(data))
    
    async def on_ready(self, room):
        print("Room {} is ready".format(room));
    
    async def on_not_ready(self, room):
        print("Room {} is NOT ready".format(room));
    
    
    async def on_connect(self):
        print("Connection established")
    
    async def on_disconnect(self):
        print("Disconnected from server")
    
    async def on_message(self, data):
        print("message received with ", data)
    

class RobotController:
    def __init__(self, url):
        # create signaling and peer connection
        self.session = SignalingSession(url, self)
        self.pc = RTCPeerConnection()
        
        # create media source
        self.player = MediaPlayer('/dev/video0', format='v4l2', options={
            'video_size': '640x480'
        })
    
    async def destroy(self):
        await self.pc.close()
        await self.session.destroy()
    
    async def prepare(self):
        await self.session.create()

        # configure media
        media = {'audio': False, 'video': True}
        if self.player and self.player.audio:
            self.pc.addTrack(self.player.audio)
            media['audio'] = True

        if self.player and self.player.video:
            self.pc.addTrack(self.player.video)
        else:
            self.pc.addTrack(VideoStreamTrack())

        # join video room
        plugin = await self.session.attach('robot1')
#    await plugin.send({
#        'body': {
#            'display': 'aiortc',
#            'ptype': 'publisher',
#            'request': 'join',
#            'room': room,
#        }
#    })

#    # send offer
#    await pc.setLocalDescription(await pc.createOffer())
#    request = {'request': 'configure'}
#    request.update(media)
#    response = await plugin.send({
#        'body': request,
#        'jsep': {
#            'sdp': pc.localDescription.sdp,
#            'trickle': False,
#            'type': pc.localDescription.type
#        }
#    })

#    # apply answer
#    answer = RTCSessionDescription(
#        sdp=response['jsep']['sdp'],
#        type=response['jsep']['type'])
#    await pc.setRemoteDescription(answer)

#    # exchange media for 10 minutes
#    print('Exchanging media')
#    await asyncio.sleep(600)

def sighandler(signame):
    print("Received signal %s" % signame)
    loop.stop()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Glob'ibulle controller")
    parser.add_argument('url', help='Signaling server URL, e.g. http://localhost:8080/')
    parser.add_argument('--verbose', '-v', action='count')
    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    
    # create the controller
    controller = RobotController(args.url)
    
    # prepare the event loop
    loop = asyncio.get_event_loop()
    
    # register signal handler
    for signame in ('SIGINT', 'SIGTERM'):
        loop.add_signal_handler(getattr(signal, signame), functools.partial(sighandler, signame))
    
    try:
        loop.run_until_complete(controller.prepare())
        loop.run_forever()
    finally:
        loop.run_until_complete(controller.destroy())
        loop.close()
