
# Common errors

`daqmx.errors.DaqError: Some or all of the samples requested have not yet been acquired.`

This is typically caused by plexon data acquisition not being started. The plexon system only generates the needed clock signal while data acquisition is running.

If neural data is not being collected the clock source can be switched to internal.

---

`daqmx.errors.DaqError: The specified resource is reserved. The operation could not be completed as specified.`

Ensure no other instances of the tilt control program is running, including in monitor mode. If this doesn't work the python processes may need to be killed with task manager.

The device can be made available by resseting it in NI Max but this can leave left over processes that can still interact with other shared resources so it is likely better to restart the computer.

This can also be resolved by restarting the computer.
