
parts:  
* the blue rectangular piece called the DI Status indicator
* the small green piece called the DI Generator

# Usage

For your testing, please go into the OmniPlex Server software and set Port A to “Event Word” Mode and set Port B to “Individual Events” mode. Please set the logic to High True for both ports for the testing. Chapter 10 of the OmniPlex User Guide https://plexon.com/wp-content/uploads/2020/01/OmniPlex-User-Guide.pdf provides useful information for setting up this configuration.

The first thing you can try is simply plugging in the DI Status indicator piece (the blue rectangular piece) first into Port A, and then next into Port B. When you do this, is every light on the DI Status Indicator illuminating in each case? This would be expected behavior if so. If this does not happen, please let us know. The behavior for LEDs “A”, “B”, and “C” is not strictly defined,  so if you see different behavior for those three LEDs specifically, that is not problematic.

After verifying the above, then next please plug the DI Status Indicator piece back into Port A. Then, plug the DI Generator (the small green item) into the other end of the DI Status Indicator. When the DI Generator is plugged in, it receives power from the Digital Input card, and this causes the DI Generator to generate a pattern of digital signals. When the DI Generator is plugged to the Digital Input card, it repeats the following pattern:

It raises bit 0, then raises and lowers the STROBE bit, then it lowers bit 0. For each of the remaining output bits (1 to 15), the generator continues this pattern. It raises the bit, raises and lowers the STROBE bit, and then lowers the bit. Finally, after bit 15 has been lowered, the DI generator raises and lowers the RSTART bit.

When  you run through this process with the DI Generator plugged into Port A (Event Word mode), the raising of the STROBE bit generates a strobed event in OmniPlex. The strobed event has a value associated with it corresponding to the setting of the individual bits at the time the STROBE was raised. Sine the DI generator raises one bit at a time, 16 strobed event values are generated (1,2,4,8…32768).

When you run through this process with the DI Generator plugged into Port B (Individual Events mode), the raising of a single bit generates a corresponding event in PlexControl software. Bit 0 creates an event 1 (EVT17 since port B corresponds to EVT17-EVT32), bit 1 creates EVT18, etc. In this mode, raising the STROBE bit does not generate any events.

In either of the test modes mentioned above, the rising of the RSTART bit generates an RSTART event and the lowering of the RSTART bit creates an RSTOP event. Note however that only Port A on the Digital Input card generates RSTART and RSTOP events.

If you’d like you can make one short (~10-20 second) PL2 file recording for each of the Ports using the above testing set-up described for each port, and you can send us these short recordings, so that we can look at the recordings in the NeuroExplorer software.
