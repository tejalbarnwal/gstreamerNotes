#!/usr/bin/env python3

import sys
import gi

gi.require_version('Gst', '1.0')
gi.require_version('GLib', '2.0')
gi.require_version('GObject', '2.0')

from gi.repository import Gst, GObject


# handler for pad added signal
def pad_added_handler(src, new_pad, data):
    print("recived new pad ", new_pad.get_name(), " from " , src.get_name())

    # if our convrter is already linked, we have nothing to do here
    if new_pad.is_linked():
        print("we are already linked, ignore")
        return
    
    new_pad_type = new_pad.query_caps(None).to_string()
    print("new pad is of type: ", new_pad_type)

    if new_pad_type.startswith("video/x-raw"):
        ret = new_pad.link(data["video_convert"].get_static_pad("sink"))
        return
    elif new_pad_type.startswith("audio/x-raw"):
        ret = new_pad.link(data["convert"].get_static_pad("sink"))
        return
    else:
        print("pad type is very different than what is expected")
        return




data =  dict()

Gst.init(None)


# create elements
data["source"] = Gst.ElementFactory.make("uridecodebin", "source")
data["convert"] = Gst.ElementFactory.make("audioconvert", "convert")
data["resample"] = Gst.ElementFactory.make("audioresample", "resample")
data["sink"] = Gst.ElementFactory.make("autoaudiosink", "sink")

data["video_convert"] = Gst.ElementFactory.make("videoconvert", "video_convert")
data["video_sink"] = Gst.ElementFactory.make("autovideosink", "video_sink")

# create empty pipeline
pipeline = Gst.Pipeline.new("test_pipeline")

if not data["source"] or not data["convert"] or not data["resample"] or not data["sink"] or not data["video_convert"] or not data["video_sink"] or not pipeline:
    print("elements couldnt be created")
    exit(-1)



pipeline.add(data["source"])
pipeline.add(data["convert"])
pipeline.add(data["resample"])
pipeline.add(data["sink"])
pipeline.add(data["video_convert"])
pipeline.add(data["video_sink"])


if not Gst.Element.link(data["convert"], data["resample"]):
    print("cnvrtr couldnt be linked to resample")
    exit(-1)

if not Gst.Element.link(data["resample"], data["sink"]):
    print("resample couldnt be linked to sink")
    exit(-1)

if not Gst.Element.link(data["video_convert"], data["video_sink"]):
    print("video convert not linked to video sink")
    exit(-1)

# source linking done later

# set the uri to play
data["source"].set_property("uri", "http://docs.gstreamer.com/media/sintel_trailer-480p.webm")

# connect to pad-added signal
data["source"].connect("pad-added", pad_added_handler, data)


# start playing
ret = pipeline.set_state(Gst.State.PLAYING)
if ret == Gst.StateChangeReturn.FAILURE:
    print("unable to set the pipeline to playing state")
    exit(-1)



# wait until error or EOS
bus = pipeline.get_bus()

while True:
    msg = bus.timed_pop_filtered(Gst.CLOCK_TIME_NONE, Gst.MessageType.STATE_CHANGED | Gst.MessageType.ERROR | Gst.MessageType.EOS)
    if msg.type == Gst.MessageType.ERROR:
        err, debug = msg.parse_error()
        print("error rececived from", msg.src.get_name(), " : ", err)
        print("debug info: ", debug)
        break
    elif msg.type == Gst.MessageType.EOS:
        print("end of stream reached")
        break
    elif msg.type == Gst.MessageType.STATE_CHANGED:
        if isinstance(msg.src, Gst.Pipeline):
            old_state, new_state, pending_state = msg.parse_state_changed()
            print("pipeline state changed from %s to %s." % (old_state.value_nick, new_state.value_nick))
    else:
        print("unexpected msg received")

pipeline.set_state(Gst.State.NULL)

