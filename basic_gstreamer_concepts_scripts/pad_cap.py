#!/usr/bin/env python3

import sys
import gi

gi.require_version('Gst', '1.0')
gi.require_version('GLib', '2.0')
gi.require_version('GObject', '2.0')

from gi.repository import Gst, GLib, GObject
import matplotlib.pyplot as plt


# the first three function help in display the capabilities structure in hum friendly format
# Check GstCap Docs

def print_field(Gquark, GValue, pfx):
    string_ = Gst.value_serialize(GValue)
    print(pfx, GLib.quark_to_string(Gquark), string_)
    return True


def print_caps(caps):
    pfx = str()
    if caps is None:
        return
    if caps.is_any():
        print("any")
        return
    if caps.is_empty():
        print("empty")
        return
    for i in range(caps.get_size()):
        structure = caps.get_structure(i)
        print("structure name: ", structure.get_name())
        structure.foreach(print_field, pfx)


def print_pad_templates_info(element_factory):
    print("pad templates for: ", Gst.ElementFactory.get_name(element_factory))
    if (not Gst.ElementFactory.get_num_pad_templates(element_factory)):
        print("none")
        return
    
    pads_list = Gst.ElementFactory.get_static_pad_templates(element_factory)

    # while(pads_list):
    #     print(type(pads_list))
    #     padtemplate = pads_list.data
    #     pads = pads_list.next
    for padtemplate in pads_list:
        
        if(padtemplate.direction == Gst.PadDirection.SRC):
            print("src template: ", padtemplate.name_template)
        elif (padtemplate.direction == Gst.PadDirection.SINK):
            print("sink template: ", padtemplate.name_template)
        else:
            print("Unknown template: ", padtemplate.name_template)
            
        
        if (padtemplate.presence == Gst.PadPresence.ALWAYS):
            print("availability: Always")
        elif (padtemplate.presence == Gst.PadPresence.SOMETIMES):
            print("availability: sometimes")
        elif (padtemplate.presence == Gst.PadPresence.REQUEST):
            print("availability: on request")
        else:
            print("availability: unknown")
            
        
        if (padtemplate.static_caps.string):
            print("capabilities: ")
            caps = padtemplate.static_caps.get()
            print_caps(caps)
            
        print("\n")


# print the CURRENT capabilites of the requested pad in the given element
def print_pad_caps(element, pad_name):
    # retrieve pad
    pad = element.get_static_pad(pad_name)
    if not pad:
        print("could not retrieve pad")
        return
    
    # retreive negotiated caps (or acceptable caps if negotiation is not finished yet)
    caps = pad.get_current_caps()
    if not caps:
        caps = pad.query_caps(None)
    
    # print and free
    print("pad: ", pad_name)
    print("caps for the this pad: ")
    print_caps(caps)



# init gstreamer
Gst.init(None)
print("INFO: Initialize Gst\n")


# create elements factory
source_factory = Gst.ElementFactory.find("audiotestsrc")
sink_factory = Gst.ElementFactory.find("autoaudiosink")
print("INFO: Element factories for audio source and sink created\n")

if not source_factory or not sink_factory:
    print("element factories couldnt be created")
    exit(-1)


# print information about the pad templates of these factories
print("INFO: pad template info for audio source factory is as follows ==>")
print_pad_templates_info(source_factory)

print("INFO: pad template info for audio sink is as follows ==>")
print_pad_templates_info(sink_factory)


# ask factories to instantiate actual elements
source = Gst.ElementFactory.create(source_factory, "source")
sink = Gst.ElementFactory.create(sink_factory, "sink")
print("INFO: audio source and sink element created from factory elements\n")

pipeline = Gst.Pipeline.new("test-pipeline")
print("INFO: pipeline is created\n")

if not source or not sink or not pipeline:
    print("elements couldnt be created")
    exit(-1)


# build pipeline
pipeline.add(source)
pipeline.add(sink)
print("INFO: audio source and sink have been added to pipeline\n")

if not Gst.Element.link(source, sink):
    print("source cant be linked to sink")
    exit(-1)


# print initial negotitiated caps(in NULL state)
print("INFO: initial NULL State related info ==> ")
print_pad_caps(sink, "sink")
print("\n")


# start playing
ret = pipeline.set_state(Gst.State.PLAYING)
print("INFO: pipeline set to playing")
if ret == Gst.StateChangeReturn.FAILURE:
    print("unable to set the pipeline in playing state")
    exit(-1)


# wait until EOS or error
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
            print("\n")
            print("INFO: pipeline state changed from %s to %s." % (old_state.value_nick, new_state.value_nick))
            print_pad_caps(sink, "sink")
            print("\n")
    else:
        print("unexpected msg received")
        break

pipeline.set_state(Gst.State.NULL)