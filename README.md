# gstreamerNotes
collection of my documenation and experimentation with GStreamer

### Theory:
GStreamer is a framework for creating, manipulating and playing multimedia.  With Gstreamer you will be creating and assembling several objects called Elements which handle the data and pass it off to the next element in line.

Gtreamer contains following types of elements:
1. Source: brings data from the outside world to the GStreamer pipeline
2. Sink: Take the GStreamer pipeline to your application memory or expose the pipeline output to hardware devices such as a monitor or a dump file
3. filter/ codec/ converter: has input and output both; transforms the input in a certain way, such as changing frame rate, parsing the incoming stream, etc
4. splitter/ muxer/ demux: split the stream into multiple branches or combine them
5. CAPS filter: filter the type of data that can pass through it
6. Bin: contains many elements within itself

A GStreamer pipeline is basically a directed graph of elements that are interconnected to give rise to a flow of operations that start from a source element and end at sink element.
An example pipeline:
```
V4l2src -> video/ x raw format -> videoconvert -> ximagesink
```
where, <br>
V4l2src: source element <br>
video/ x raw format=YUV2 : CAPS filter <br>
videoconvert: filter element <br>
ximagesink: sink element <br>

Each element of the pipeline can be in any of the four states(`NULL`, `READY`, `PAUSED`, `PLAYING`)
Find more about these states at [link](https://sahilchachra.medium.com/all-you-want-to-get-started-with-gstreamer-in-python-2276d9ed548e).


Elements communicate with each other using pads. Pads have two properties, their direction and their availability.  There are two pad directions, source and sink.  Elements receive data with their sink pads and push data to their source pads.  In our first terminal example above, we had three elements: filesrc, decodebin, and autoaudiosink.  Filesrc receives a file and pushes it to its source pad. This makes it available for decodebin to accept it on its sink pad.  When it receives that data it manipulates it and pushes it to its source pad.  Now autoaudiosink can accept that data on its sink pad and within that element, it plays it on your computers speakers.
The availability property is far more confusing.  There are three types of availability.  Always, Sometimes (AKA Dynamic), and Request. Always pads, always exist, Sometimes pads exist only in certain cases, and Request pads exist when you tell them to otherwise they are not present and will not be able to connect to anything.


In GStreamer, both signal handlers and probe callbacks are mechanisms used for intercepting and handling events within the GStreamer pipeline, but they serve different purposes and are used in different contexts.

Signal Handlers:
Signal handlers in GStreamer are functions that are connected to specific signals emitted by GStreamer elements.
These signals indicate various events that occur during the processing of multimedia data, such as state changes, errors, and end-of-stream events.
Signal handlers are typically used to react to high-level events in the pipeline, such as when a state change occurs (e.g., from PLAYING to PAUSED), when an error is encountered, or when the pipeline finishes processing data.
Signal handlers are added using the g_signal_connect() function from GLib, or its equivalent in the language bindings used with GStreamer (e.g., gst_element_connect() in PyGObject).
Examples of signals include message, eos (end-of-stream), error, state-changed, etc.

Probe Callbacks:
Probe callbacks in GStreamer are functions that are attached to specific pads of GStreamer elements.
They allow you to intercept and examine data as it flows through the pipeline, providing a way to inspect and manipulate buffers and events at various points in the pipeline.
Probe callbacks are commonly used for tasks such as debugging, performance analysis, and implementing custom processing algorithms.
Probes can be attached to pads in different directions: GST_PAD_PROBE_TYPE_SRC for probes on source pads (output data) and GST_PAD_PROBE_TYPE_SINK for probes on sink pads (input data).
Probes can be set to run either before or after the data has been processed by the element using GST_PAD_PROBE_TYPE_BLOCK and GST_PAD_PROBE_TYPE_IDLE, respectively.
Probes are added to pads using functions like gst_pad_add_probe().
In summary, signal handlers are used to react to high-level events in the GStreamer pipeline, while probe callbacks are used to intercept and manipulate data as it flows through the pipeline for low-level inspection and processing purposes. Both mechanisms are powerful tools for building sophisticated multimedia applications with GStreamer.


You can find the python version of GStreamer tutorials at [link](https://github.com/gkralik/python-gst-tutorial).


References:
* https://youtu.be/VLxAkmi9K-M?si=rrS4arep-TRchOfB 
* https://markwingerd.wordpress.com/2014/11/19/using-gstreamer-with-python/