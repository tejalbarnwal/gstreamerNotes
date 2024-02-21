#!/usr/bin/env python3
import sys
import gi
import logging

gi.require_version('Gst', '1.0')
gi.require_version('GLib', '2.0')
gi.require_version('GObject', '2.0')

from gi.repository import Gst, GLib, GObject

logging.basicConfig(level=logging.DEBUG, format="[%(name)s] [%(levelname)8s] - %(message)s")
logger = logging.getLogger(__name__)

# init gstreamer
Gst.init(None)

# create elements
source = Gst.ElementFactory.make("videotestsrc", "source")
filter = Gst.ElementFactory.make("vertigotv", "filter")
converter = Gst.ElementFactory.make("videoconvert", "converter")
sink = Gst.ElementFactory.make("autovideosink", "sink")


# create empty pipeline
pipeline = Gst.Pipeline.new("test-pipeline")

if not pipeline or not source or not sink:
    logger.error("not all elements could be created")
    sys.exit(1)


# build the pipeline
pipeline.add(source)
pipeline.add(filter)
pipeline.add(converter)
pipeline.add(sink)

if not source.link(filter):
    logger.error("element source cannot be linked to filter")
    sys.exit(1)
if not filter.link(converter):
    logger.error("element filter cannot be linked to cnvrter")
    sys.exit(1)
if not converter.link(sink):
    logger.error("element convrter cant be linked to sink")
    sys.exit(1)

# modify the sources properties
source.set_property("pattern", 0)

# start playing
ret = pipeline.set_state(Gst.State.PLAYING)
if ret == Gst.StateChangeReturn.FAILURE:
    logger.error("unable to set the playing state for the pipeline")
    sys.exit(1)

# wait for error
bus = pipeline.get_bus()
msg = bus.timed_pop_filtered(Gst.CLOCK_TIME_NONE, Gst.MessageType.ERROR | Gst.MessageType.EOS)

# parse msg
if msg:
    if msg.type == Gst.MessageType.ERROR:
        err, debug_info = msg.parse_error()
        logger.error(f"Error received from element {msg.src.get_name()}: {err.message}")
        logger.error(f"Debugging information: {debug_info if debug_info else 'none'}")
    elif msg.type == Gst.MessageType.EOS:
        logger.info("End-Of-Stream reached.")
    else:
        logger.error("unexpected message recieved.")

pipeline.set_state(Gst.state.NULL)