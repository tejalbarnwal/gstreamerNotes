#!/usr/bin/env python3

import sys
import gi

gi.require_version('Gst', '1.0')

from gi.repository import Gst

pipeline = None
bus = None
message = None

# initialize Gstreamer
# automaticlly execs the command line arg
Gst.init(None)

# build the pipeline
pipeline = Gst.parse_launch(
    "playbin uri=https://gstreamer.freedesktop.org/data/media/sintel_trailer-480p.webm"
)

# start playing
pipeline.set_state(Gst.State.PLAYING)

# wait until error
bus = pipeline.get_bus()
msg = bus.timed_pop_filtered(
    Gst.CLOCK_TIME_NONE,
    Gst.MessageType.ERROR | Gst.MessageType.EOS
)

# free resources
pipeline.set_state(Gst.State.NULL)
