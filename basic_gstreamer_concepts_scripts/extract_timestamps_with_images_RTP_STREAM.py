#!/usr/bin/env python3
import sys
import gi
import logging
import cv2
import threading
import numpy as np
from datetime import datetime
import time


gi.require_version('Gst', '1.0')
gi.require_version('GLib', '2.0')
gi.require_version('GObject', '2.0')
gi.require_version('GstApp', '1.0')
gi.require_version('GstRtp', '1.0')

from gi.repository import Gst, GLib, GObject, GstApp, GstRtp

logging.basicConfig(level=logging.DEBUG, format="[%(name)s] [%(levelname)8s] - %(message)s")
logger = logging.getLogger(__name__)

class time_extractor():
    def __init__(self):
        self.setup_gst_elements()
        self.setup_gst_pipeline()
        self.prev_rtp_timestamp = 0
        self.rtcp_ntp_timestamp = 0
        self.rtcp_rtp_timestamp = 0
        self.first_rtcp_recv = False
        self.prev_timestamp = 0.0
    
    
    def setup_gst_elements(self):
        # create element for rtp udp
        self.rtp_udpsrc_address = "192.168.0.141"
        self.rtp_udpsrc_port = 11024
        self.rtp_udpsrc_caps_string = "application/x-rtp, media=video, clock-rate=90000, encoding-name=H264, payload=96"
        self.rtp_udpsrc_caps = Gst.caps_from_string(self.rtp_udpsrc_caps_string)

        self.rtp_udpsrc = Gst.ElementFactory.make("udpsrc", "rtp_udpsrc")
        self.rtp_udpsrc.set_property("address", self.rtp_udpsrc_address)
        self.rtp_udpsrc.set_property("port", self.rtp_udpsrc_port)
        self.rtp_udpsrc.set_property("caps", self.rtp_udpsrc_caps)
        
        # create element for rtcp udp
        self.rtcp_udpsrc_address = "192.168.0.141"
        self.rtcp_udpsrc_port = 11028
        self.rtcp_udpsrc_caps_string = "application/x-rtcp"
        self.rtcp_udpsrc_caps = Gst.caps_from_string(self.rtcp_udpsrc_caps_string)

        self.rtcp_udpsrc = Gst.ElementFactory.make("udpsrc", "rtcp_udpsrc")
        self.rtcp_udpsrc.set_property("address", self.rtcp_udpsrc_address)
        self.rtcp_udpsrc.set_property("port", self.rtcp_udpsrc_port)
        self.rtcp_udpsrc.set_property("caps", self.rtcp_udpsrc_caps)

        # create element for rtpbin
        self.rtpbin = Gst.ElementFactory.make("rtpbin", "rtpbin")

        # create elements for processing rtp packets
        self.rtpToh264 = Gst.ElementFactory.make("rtph264depay", "rtpToh264")
        self.queue_ = Gst.ElementFactory.make("queue", "queue_")
        self.h264parse_ = Gst.ElementFactory.make("h264parse", "h264parse_")

        self.nv_decoder = Gst.ElementFactory.make("nvv4l2decoder", "nv_decoder")
        self.nv_decoder.set_property("enable-max-performance", True)

        self.nv_conv = Gst.ElementFactory.make("nvvidconv", "nv_conv")

        self.video_sink = Gst.ElementFactory.make("xvimagesink", "video_sink")
        self.video_sink.set_property("sync", True)
    
    
    def setup_gst_pipeline(self):
        # create new pipeline
        self.pipeline = Gst.Pipeline.new("test_pipeline")

        if not self.rtp_udpsrc or not self.rtcp_udpsrc or not self.rtpbin or not self.rtpToh264 or not self.queue_ or not self.h264parse_ or not self.nv_decoder or not self.nv_conv or not self.video_sink or not self.pipeline:
            print("elements couldnt be created")
            exit(-1)

        # add elements to the pipeline
        self.pipeline.add(self.rtp_udpsrc)
        self.pipeline.add(self.rtcp_udpsrc)
        self.pipeline.add(self.rtpbin)
        self.pipeline.add(self.rtpToh264)
        self.pipeline.add(self.queue_)
        self.pipeline.add(self.h264parse_)
        self.pipeline.add(self.nv_decoder)
        self.pipeline.add(self.nv_conv)
        self.pipeline.add(self.video_sink)

        # link elements
        # if not Gst.Element.link(rtpbin, rtpToh264):
        #     print("rtpbin couldnt be linked to h264parse")
        #     exit(-1)

        if not Gst.Element.link(self.rtpToh264, self.queue_):
            print("ERR: rtp to h264 decoder cant be linked to queue")
            exit(-1)
            
        if not Gst.Element.link(self.queue_, self.h264parse_):
            print("ERR: queue is not linked to h264 parse")
            exit(-1)
            
        if not Gst.Element.link(self.h264parse_, self.nv_decoder):
            print("ERR: h264parse is not linked to nv decoded")
            exit(-1)
            
        if not Gst.Element.link(self.nv_decoder, self.nv_conv):
            print("ERR: nv_decoder not linked to nv conv")
            exit(-1)
            
        if not Gst.Element.link(self.nv_conv, self.video_sink):
            print("ERR: nv conv cant be linked to video sink")
            exit(-1)
            

        self.rtp_recv_sink_pad_template = self.rtpbin.get_pad_template("recv_rtp_sink_%u")
        self.rtp_recv_sink_pad = self.rtpbin.request_pad(self.rtp_recv_sink_pad_template, "recv_rtp_sink_0", None)
        print("INFO: obtained request pad < ", self.rtp_recv_sink_pad.get_name(), " > for rtp sink for rtpbin")

        self.rtcp_recv_sink_pad_template = self.rtpbin.get_pad_template("recv_rtcp_sink_%u")
        self.rtcp_recv_sink_pad = self.rtpbin.request_pad(self.rtcp_recv_sink_pad_template, "recv_rtcp_sink_0", None)
        print("INFO: obtained request pad < ", self.rtcp_recv_sink_pad.get_name(), " > for rtcp sink for rtpbin")

        self.rtp_udpsrc_pad = self.rtp_udpsrc.get_static_pad("src")
        self.rtcp_udpsrc_pad = self.rtcp_udpsrc.get_static_pad("src")



        if self.rtp_udpsrc_pad.link(self.rtp_recv_sink_pad) != Gst.PadLinkReturn.OK:
            print("ERR: rtp udp src and rtp rtpbin sink cant be linked")
            exit(-1)

        if self.rtcp_udpsrc_pad.link(self.rtcp_recv_sink_pad) != Gst.PadLinkReturn.OK:
            print("ERR: rtp udp src and rtp rtpbin sink cant be linked")
            exit(-1)
    
    
    def pad_added_handler(self, src, new_pad, element_for_sink):
        print("recieved new pad < ", new_pad.get_name(), " > from < ", src.get_name(), " >")
        
        if new_pad.is_linked():
            print("we are already linked, ignore")
            return
        
        new_pad_type = new_pad.query_caps(None).to_string()
        print("new pad is of type < ", new_pad_type, " >")
        
        if new_pad_type.startswith("application/x-rtp"):
            ret = new_pad.link(element_for_sink.get_static_pad("sink"))
            return
        else:
            print("pad type is very different that what is expected")
            return
    
    
    def on_receiving_rtcp_callback(self, session, buffer):
        rtcp_buffer = GstRtp.RTCPBuffer()
        rtcp_pkt = GstRtp.RTCPPacket()
        
        res = GstRtp.RTCPBuffer.map(buffer, Gst.MapFlags.READ, rtcp_buffer)
        new_pkt = rtcp_buffer.get_first_packet(rtcp_pkt)
        
        while True:
            rtcp_pkt_type = rtcp_pkt.get_type()
            if (rtcp_pkt_type == GstRtp.RTCPType.SR):
                self.first_rtcp_recv = True
                sender_info = rtcp_pkt.sr_get_sender_info()
                print("----------------------------------------------------------")
                print("type of sender info: ", type(sender_info))
                print("type of sender info ntp time: ", type(sender_info[1]))
                print("type of sender info rtp time: ", type(sender_info[2]))
                
                self.rtcp_ntp_timestamp = GstRtp.rtcp_ntp_to_unix(sender_info[1])
                self.rtcp_rtp_timestamp = sender_info[2]
                print("ntp timestamp unix ns: ", self.rtcp_ntp_timestamp)
                print("rtp timestamp: ", self.rtcp_rtp_timestamp)
                print("----------------------------------------------------------")
                
            ### why do we want to move to next?
            if not(rtcp_pkt.move_to_next()):
                # print("ERR: rtcp packet pointer pointing to invalid packet")
                break
    
    
    def calculate_timestamp(self, pad, info):
        if self.first_rtcp_recv:
            res, rtp_buffer = GstRtp.RTPBuffer.map(info.get_buffer(), Gst.MapFlags.READ)
            rtp_timestamp = rtp_buffer.get_timestamp()
            if not (self.prev_rtp_timestamp == rtp_timestamp):
                print('type of rtp timestamp: ', type(rtp_timestamp))
                print("rtp timestamp: ",float(rtp_timestamp))
                print("diff wrt prev: ", rtp_timestamp - self.prev_rtp_timestamp)
                
                
                rtp_diff_wrt_rtcp = (rtp_timestamp - self.rtcp_rtp_timestamp) / 90000.0
                print("rtp_diff_wrt_rtcp: ", rtp_diff_wrt_rtcp)
                abs_timestamp = (self.rtcp_ntp_timestamp/1000000000.0) + rtp_diff_wrt_rtcp
                print("derived ntp: ", (self.rtcp_ntp_timestamp/1000000000.0))
                print("abs_timestamp: ", abs_timestamp)
                print(datetime.utcfromtimestamp(abs_timestamp).strftime('%Y-%m-%d %H:%M:%S'))
                
                print("diff in msec from prev frame: ", (abs_timestamp - self.prev_timestamp) * 1000.0)
                print("--------------------------------------------------------------------")
                self.prev_rtp_timestamp = rtp_timestamp
                self.prev_timestamp = abs_timestamp
        return Gst.PadProbeReturn.OK
    
    
    def thread_func_rtp_decoder(self):
        self.rtpbin.connect("pad-added", self.pad_added_handler, self.rtpToh264)
        #  get the session and attach it to signal on recieving rtcp
        rtpsession_id = 0
        self.rtpsession = self.rtpbin.emit("get-internal-session", rtpsession_id)
        self.rtpsession.connect_after("on-receiving-rtcp", self.on_receiving_rtcp_callback)
        self.rtpToh264_sinkpad = self.rtpToh264.get_static_pad("sink")
        self.rtpToh264_sinkpad_probeid = self.rtpToh264_sinkpad.add_probe(Gst.PadProbeType.BUFFER, self.calculate_timestamp)
        
        # start playing
        ret = self.pipeline.set_state(Gst.State.PLAYING)
        if ret == Gst.StateChangeReturn.FAILURE:
            print("unable to set the pipeline to playing state")
            exit(-1)
        
        # wait until error or EOS
        bus = self.pipeline.get_bus()
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
        self.pipeline.set_state(Gst.State.NULL)
    
    
    def thread_func_opencv(self):
        while True:
            time.sleep(2)
            print("2nd thread running")
    
    
    def run(self):
        th1 = threading.Thread(target = self.thread_func_rtp_decoder)
        th2 = threading.Thread(target=self.thread_func_opencv)
        
        th1.start()
        th2.start()
        
        th1.join()
        th2.join()




if __name__ == "__main__":
    obj = time_extractor()
    Gst.init(None)
    obj.run()
