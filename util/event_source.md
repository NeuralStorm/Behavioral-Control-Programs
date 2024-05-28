
Event source values are of the form `input|output`.

`|output` can be omitted and will default to `none`.

If not set or an empty string `input` and `output` will both default to `none`.

# Examples

`bridge|bridge` will use the bridge for input and output

`neurokey|bridge` will use get data from neurokey and use the bridge for output

`plexon|plexdo` will use the plexon system for input and output

`bridge` will use the bridge for input and perform no output

# Input types

`plexon` - get data from plexon using pyopxclient

---

`neurokey`

get data from via `nkyapi_wrapper.py`, `nkyapi_lsl.py`, `nkyapi_spikes.py` and the bridge server.

---

`bridge`

get data from the bridge hardware via the bridge server

---

`none` - get no external data

# Output types

`plexdo`

Sets outputs via PlexDO or PlexDO64. The correct plexdo library will be chosen based on the host OS.

`bridge`

Sets outputs on the bridge. This directly accesses the bridge's file object and could possible cause issues if used at the same time as other software that sends commands to the bridge hardware.

`none` - disables external outputs
