import os, gi, time, sys
gi.require_version("Gst", "1.0")
from gi.repository import GObject, Gst
from sources import RTSPH264Source
from utils import must_link
from converter import H264Decode
from sink import HLSAPPSINK
from jpegenc import JpegSink
import threading
import requests
from datetime import datetime, timedelta
import shutil
from GetDuration import get_duration

from db import run_query, select_query
import time
from dotenv import load_dotenv

load_dotenv()
ROOT_PATH = os.getenv("ROOT_PATH")

Gst.init(None)
GObject.threads_init()

def CCTV_VOD_THUMBNAIL(camera_id, rtsp_url, start_video, start_thumbnail):

    pipeline = Gst.Pipeline()
    bus = pipeline.get_bus()

    first_video = start_video
    first_thumbnail = start_thumbnail
    
    flag = 0
    
    # TEST : "rtsp://83.229.5.36:1935/vod/sample.mp4"
    rtsp_uri = rtsp_url
    # Video elements.

    src = RTSPH264Source(rtsp_uri)   #### de soruce to video using H264
    pipeline.add(src)


    decoder = H264Decode()
    pipeline.add(decoder)

    recording_sink = HLSAPPSINK().genObj(
        location=camera_id
    )
    pipeline.add(recording_sink)

    jpeg_sink = JpegSink().genObj(
        location=camera_id
    )
    pipeline.add(jpeg_sink)


    videotee = Gst.ElementFactory.make("tee", "tee")
    pipeline.add(videotee)

    recording_queue = Gst.ElementFactory.make("queue", "recordqueue")
    pipeline.add(recording_queue)


    teepad_recording = videotee.get_request_pad('src_%u')
    recording_pad = recording_queue.get_static_pad('sink')


    jpeg_queue = Gst.ElementFactory.make("queue", "jpeg_queue")
    pipeline.add(jpeg_queue)


    teepad_osd =  videotee.get_request_pad('src_%u')
    jpeg_pad = jpeg_queue.get_static_pad('sink')

    try:
        must_link(src.link(decoder))
        # must_link(decoder.link(recording_sink))
        # must_link(decoder.link(osd_sink))

        must_link(decoder.link(videotee))
        must_link(teepad_recording.link(recording_pad))
        must_link(recording_queue.link(recording_sink))
        must_link(teepad_osd.link(jpeg_pad))
        must_link(jpeg_queue.link(jpeg_sink))
    except RuntimeError as err:
        raise RuntimeError('Could not link source') from err


    # Start pipeline.
    pipeline.set_state(Gst.State.PLAYING)

    while True:
        try:
            message = bus.timed_pop(Gst.SECOND)
            
            second_date = datetime.now()
            delta_video = second_date - first_video
            delta_thumbnail = second_date - first_thumbnail

            if(delta_video.total_seconds() >= 3600):
                last_date = first_video + timedelta(seconds=600)
                query = "SELECT * FROM VIDEO WHERE camera_id = {} AND time >= {} AND time <= {}".format(camera_id, datetime.strftime(first_video, "'%Y-%m-%d %H:%M:%S'"),datetime.strftime(last_date, "'%Y-%m-%d %H:%M:%S'"))
                result = select_query(query)
                for item in result:
                    delete_path = "../{}".format(item[1])
                    if os.path.exists(delete_path):
                        os.remove(delete_path)
                query = "DELETE FROM VIDEO WHERE camera_id = {} AND time >= {} AND time <= {}".format(camera_id, datetime.strftime(first_video, "'%Y-%m-%d %H:%M:%S'"),datetime.strftime(last_date, "'%Y-%m-%d %H:%M:%S'"))
                run_query(query)
                first_video = last_date
    
            if(delta_thumbnail.total_seconds() >= 3600):
                last_date = first_thumbnail + timedelta(seconds=600)
                query = "SELECT * FROM THUMBNAIL WHERE camera_id = {} AND time >= {} AND time <= {}".format(camera_id, datetime.strftime(first_thumbnail, "'%Y-%m-%d %H:%M:%S'"),datetime.strftime(last_date, "'%Y-%m-%d %H:%M:%S'"))
                result = select_query(query)
                for item in result:
                    delete_path = "../{}".format(item[1])
                    if os.path.exists(delete_path):
                        os.remove(delete_path)

                query = "DELETE FROM THUMBNAIL WHERE camera_id = {} AND time >= {} AND time <= {}".format(camera_id, datetime.strftime(first_thumbnail, "'%Y-%m-%d %H:%M:%S'"),datetime.strftime(last_date, "'%Y-%m-%d %H:%M:%S'"))
                run_query(query)
                first_thumbnail = last_date
            if message == None:
                pass
            elif message.type == Gst.MessageType.EOS or message.type == Gst.MessageType.ERROR:
                if (flag == 0):
                    query = "UPDATE camera SET online = 'NO' where id = {}".format(camera_id)
                    run_query(query)
                    flag = 1
                while(True):
                    print("OFFLINE STATUS")
                    time.sleep(2)
                    copy_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    # dst = "..{}/{}/videos/{}.ts".format(ROOT_PATH, camera_id, copy_time)
                    # shutil.copyfile("../share/gray.ts", dst)

                    r = requests.post("http://localhost:5000/api/thumbnails", json={
                            "path" : "/share/gray.jpg",
                            "time" : copy_time,
                            "camera_id" : camera_id
                        })
                    r = requests.post("http://localhost:5000/api/videos", json={
                            "path" : "/share/gray.ts",
                            "time" : copy_time,
                            "camera_id" : camera_id,
                            "duration": get_duration("../share/gray.ts")
                        })
                    query = "SELECT * FROM camera WHERE id = {}".format(camera_id)
                    list = select_query(query)
                    if list[0][5] == "YES":
                        print("CHANGED")
                        break
                break

            # elif message.type == Gst.MessageType.ERROR:
            #     if (flag == 0):
            #         query = "UPDATE camera SET online = 'NO' where id = {}".format(camera_id)
            #         run_query(query)
            #         flag = 1
            #     while(True):
            #         print("ERROR")
            #         time.sleep(2)
            #         copy_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            #         dst = "..{}/{}/videos/{}.ts".format(ROOT_PATH, camera_id, copy_time)
            #         shutil.copyfile("../share/gray.ts", dst)

            #         r = requests.post("http://localhost:5000/api/thumbnails", json={
            #                 "path" : "/share/gray.jpg",
            #                 "time" : copy_time,
            #                 "camera_id" : camera_id
            #             })
            #         r = requests.post("http://localhost:5000/api/videos", json={
            #                 "path" : "{}/{}/videos/{}.ts".format(ROOT_PATH, camera_id, copy_time),
            #                 "time" : copy_time,
            #                 "camera_id" : camera_id,
            #                 "duration": 2.0
            #             })
            #         query = "SELECT * FROM camera WHERE id = {}".format(camera_id)
            #         list = select_query(query)
            #         if list[0][5] == "YES":
            #             print("CHANGED")
            #             break
            #     break
        except KeyboardInterrupt:
            break

    print("THREAD ENDED")
    pipeline.set_state(Gst.State.NULL)