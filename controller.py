#!/usr/bin/python3

import argparse
import asyncio
import logging

import aiohttp
from aiortc import RTCPeerConnection, RTCSessionDescription, VideoStreamTrack
from aiortc.contrib.media import MediaPlayer

import socketio


class SignalingSession(socketio.AsyncClientNamespace):
    def __init__(self, url):
        socketio.AsyncClientNamespace.__init__(self)
        self._sio = None
        self._url = url

    async def create(self):
        self._sio = socketio.AsyncClient()
        self._sio.register_namespace(self)
        await self._sio.connect(self._url)
    
    async def attach(self, room):
        await self._sio.emit('create or join', room)
    
    
    async def on_created(self, data):
        print("on_created")
    
    async def on_full(self, data):
        print("on_full")
    
    async def on_join(self, data):
        print("on_join")
    
    async def on_joined(self, room, socketId):
        print("Joined room {} using socket id {}".format(room, socketId))
    
    async def on_log(self, data):
        print(' '.join(data))
    
    
    async def on_connect(self):
        print("Connection established")
    
    async def on_disconnect(self):
        print("Disconnected from server")
    
    async def on_message(self, data):
        print("message received with ", data)
    

async def run(pc, player, session):
    await session.create()

    # configure media
    media = {'audio': False, 'video': True}
    if player and player.audio:
        pc.addTrack(player.audio)
        media['audio'] = True

    if player and player.video:
        pc.addTrack(player.video)
    else:
        pc.addTrack(VideoStreamTrack())

    # join video room
    plugin = await session.attach('Robot')
#    await plugin.send({
#        'body': {
#            'display': 'aiortc',
#            'ptype': 'publisher',
#            'request': 'join',
#            'room': room,
#        }
#    })

    # send offer
    await pc.setLocalDescription(await pc.createOffer())
    request = {'request': 'configure'}
    request.update(media)
    response = await plugin.send({
        'body': request,
        'jsep': {
            'sdp': pc.localDescription.sdp,
            'trickle': False,
            'type': pc.localDescription.type
        }
    })

    # apply answer
    answer = RTCSessionDescription(
        sdp=response['jsep']['sdp'],
        type=response['jsep']['type'])
    await pc.setRemoteDescription(answer)

    # exchange media for 10 minutes
    print('Exchanging media')
    await asyncio.sleep(600)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Glob'ibulle controller")
    parser.add_argument('url', help='Signaling server URL, e.g. http://localhost:8080/')
    parser.add_argument('--verbose', '-v', action='count')
    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)

    # create signaling and peer connection
    session = SignalingSession(args.url)
    pc = RTCPeerConnection()

    # create media source
    player = MediaPlayer('/dev/video0', format='v4l2', options={
        'video_size': '640x480'
    })

    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(run(
            pc=pc,
            player=player,
            session=session))
    except KeyboardInterrupt:
        pass
    finally:
        loop.run_until_complete(pc.close())
        loop.run_until_complete(session.destroy())
