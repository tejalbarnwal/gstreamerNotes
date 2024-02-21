#!/usr/bin/env python3
import sys
import gi
import logging
import cv2
import threading
import numpy as np

gi.require_version('Gst', '1.0')
gi.require_version('GLib', '2.0')
gi.require_version('GObject', '2.0')
gi.require_version('GstApp', '1.0')

from gi.repository import Gst, GLib, GObject, GstApp

logging.basicConfig(level=logging.DEBUG, format="[%(name)s] [%(levelname)8s] - %(message)s")
logger = logging.getLogger(__name__)
Gst.init(None)

class Interpreter():
    def __init__(self):
        self.source = Gst.ElementFactory.make("videotestsrc", "source")
        self.filter = Gst.ElementFactory.make("vertigotv", "filter")
        self.converter = Gst.ElementFactory.make("videoconvert", "converter")
        self.caps_filter = Gst.ElementFactory.make("capsfilter", "capsfilter_")
        
        self.sink = Gst.ElementFactory.make("appsink")
        
        self.pipeline = Gst.Pipeline.new("test-pipeline")
        
        if not self.pipeline or not self.source or not self.sink:
            logger.error("not all elements could be created")
            sys.exit(1)
            
        self.pipeline.add(self.source)
        self.pipeline.add(self.filter)
        self.pipeline.add(self.converter)
        self.pipeline.add(self.caps_filter)
        self.pipeline.add(self.sink)
        
        self.caps_filter.set_property("caps", Gst.caps_from_string("video/x-raw,format=BGR"))
        
        if not self.source.link(self.filter):
            logger.error("element source cannot be linked to filter")
            sys.exit(1)
        if not self.filter.link(self.converter):
            logger.error("element filter cannot be linked to cnvrter")
            sys.exit(1)
        if not self.converter.link(self.caps_filter):
            logger.error("element convrter cant be linked to caps filter")
            sys.exit(1)
        if not self.caps_filter.link(self.sink):
            logger.error("element caps filter cant be linked to sink")
            sys.exit(1)

        # modify the sources properties
        self.source.set_property("pattern", 0)
        

        self.sink.set_property("emit-signals", True)
        self.sink.connect("new-sample", self.on_sink_new_sample)
        
        self.img = None
        self.publish_img = False

    
    def on_sink_new_sample(self, appsink):
        sample = appsink.pull_sample()
        caps = sample.get_caps()
        
        height = caps.get_structure(0).get_value("height")
        width = caps.get_structure(0).get_value("width")
        print("h: ", height)
        print("w: ", width)
        
        buffer = sample.get_buffer()
        print(caps, "   buffer size: ", buffer.get_size())
        res, map_info = buffer.map(Gst.MapFlags.READ)
        
        if not res:
            raise RuntimeError("could not map buffer data!")
        
        self.img = np.ndarray(shape=(height, width, 3), 
                                    dtype=np.uint8,
                                    buffer=map_info.data)
        buffer.unmap(map_info)
        self.publish_img = True
        
        return Gst.FlowReturn.OK
    
    
    def thread1(self):
        # start playing
        ret = self.pipeline.set_state(Gst.State.PLAYING)
        if ret == Gst.StateChangeReturn.FAILURE:
            logger.error("unable to set the playing state for the pipeline")
            sys.exit(1)
        
        # wait for error
        bus = self.pipeline.get_bus()
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

        self.pipeline.set_state(Gst.state.NULL)

    def thread2(self):
        while True:
            if self.publish_img:
                print("img showing")
                cv2.imshow("frame", self.img)
                if cv2.waitKey(1) == ord('q'):
                    break   
                self.publish_img = False
    
    def run(self):
        th1 = threading.Thread(target = self.thread1)
        th2 = threading.Thread(target = self.thread2)
        
        th1.start()
        th2.start()
        
        th1.join()
        th2.join()



if __name__ == "__main__":
    obj = Interpreter()
    obj.run()
