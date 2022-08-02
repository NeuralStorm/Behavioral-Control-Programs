
# Setup

Install dependencies  
`pip install -r requirements.txt`

If using live graph view  
`pip install pyside6`  
if installation fails use  
`pip install pyside2==5.15.2`  

# Usage

Example command line call
```bash
python main.py --config config.hjson
```

## Usage examples

Create a copy of `../tilt_docs/data_collection_template`.

`clock_source` will need to be changed to "internal" in `config.hjson` if running without the plexon system.

### Bias Collection

Run `run_bias.sh` in the data collection directory.

This will create a dated bias file.

### Open loop

Edit `config.hjson`; ensure `mode` is set to open_loop. Set `num_tilts` and `delay_range` to the desired values. `baseline`, `sham`, `reward` and `channels` can be ignored or removed from the config file.

Collect a bias file by running `run_bias.sh`.

Run `run_tilts.sh` in the data collection directory.  
This will read settings from `config.hjson` and create dated output files in the data collection directory.

The program will run through the specified number of tilts then wait for the user to press enter before exiting.

---
### Closed loop, initial run

Edit `config.hjson`; set `mode` to closed_loop, `baseline` to true and `sham` to false. Set `num_tilts`, `delay_range` and`reward` to the desired values.

Run `run_tilts.sh` in the data collection directory.  
This will read setting from `config.hjson` and create dated output files in the data collection directory.

The program will perform tilts and record the tilts and spikes.

---
### Closed loop, after initial run

Edit config used for the initial run and change `baseline` to false.  
Add `--template-in <file>` where `<file>` is the name of the template.json file created by the initial run.  
If a template file wasn't generated or different settings are needed a new template file can be generated using build_template.py.

Create or edit `labels.hjson`; set `channels` to the desired value. See [example_labels.hjson](./example_labels.hjson) for an example.

Run `run_tilts.sh` in the data collection directory.  
This will read settings from `config.hjson` and create dated output files in the data collection directory. Euclidian classifier templates are loaded from the specified template.json file.

The program will perform tilts and attempt to classify the tilt type based on the created templates and perform punish/reward actions based on if the classification was correct.

---
### Live view

Add the `--live` parameter to enable the live view.
```
python main.py --config config.hjson --monitor --live
```

### Calibrated live view

The path `/grf_python` will need to be substituted with the location of grf_python on your system ([Behavior-Analysis-Programs](https://github.com/moxon-lab-codebase/Behavior-Analysis-Programs), tested with commit `5f005e1a5530fd36f4ea0879e8453bc01a65871b`)

The environment variable `grf_python_path` must be set to the location of grf python.
e.g.  
`fish`
```
set -gx grf_python_path /grf_python
```
`bash`
```
export grf_python_path=/grf_python
```
`windows`
```
set grf_python_path=/grf_python
```

The python dependencies for grf_python will need to be installed.

Run the program
```
python main.py --config your_config.hjson --monitor --live-cal --live-bias ./your_bias_file
```

---
## Pausing

pressing enter will pause the program at the end of the current tilt. pressing enter will resume the program, pressing q then enter will exit the program

## Notes on clocks

Plexon outputs a 40khz clock signal. This is downsampled by a hardware downsampler to 1000hz and sent to Dev6/PFI6. Note that data collection must be started for the plexon system to output its 40khz clock.

Using plexon's clock signal instead of the internal nidaq clock means, given one known shared event (such as the start pulse), all the neural and grf data can be correlated in time. Without using a shared clock the two clocks will experience a different amount of drift and diverge over time.

clock_source should always be set to external in normal use.

## Strain guage reading recording

Strain guage data is recorded concurrently with the rest of the program.

Note: In some places the analysis pipeline refers to the side with two sensors as the hindlimbs but they could be the forelimbs if the animal is placed on the platform facing the other direction.  
With the forelimbs on a single sensor the sensor numbers correspond to the following limbs.  
sensor1: right hind limb  
sensor2: left hind limb  
sensor3: forelimbs

The output csv contains the following columns.

```
sensor1_s1
sensor1_s2
sensor1_s3
sensor1_s4
sensor1_s5
sensor1_s6
sensor2_s1
sensor2_s2
sensor2_s3
sensor2_s4
sensor2_s5
sensor2_s6
sensor3_s1
sensor3_s2
sensor3_s3
sensor3_s4
sensor3_s5
sensor3_s6
Strobe: signal that gos high when a tilt starts and low when it finishes
Start: ttl pulse indicating start of plexon recording
Inclinometer: Inclinometer
Timestamp: Timestamp (incremented by 1/sample rate for each row)
strobe_digital: digital version of Strobe passed through a schmidt trigger
tilt_midpoint: signal that gos high when the tilt reaches it's maximum inclination
stim: ttl pulse indicating stimulation was applied
```

# Program flow

The program has multiple modes, set with the `mode` config parameter. The behaviour of the different modes is listed below. Recording of analog data is handled the same way for all modes except bias (where live view can not be used). Stimulation works the same for all modes except bias and monitor where stimulation is not available.

## open_loop

```
create a list of tilt types
wait for start pulse
for i in 0..num_tilts:
    perform tilt i
    wait for after_tilt_delay
    if reward enabled:
        dispense water
    wait for a random time within delay_range
waits for the user to press enter
```

## closed_loop (baseline = true, yoked = false)

```
create a list of tilt types
wait for start pulse
for i in 0..num_tilts:
    clear pending plexon events
    start tilt i
    for event recieved from plexon within about 200ms:
        if event is a tilt:
            add event to classifier
        if event is a spike:
            add spike to classifier
    finish tilt
    wait for after_tilt_delay
    if reward enabled:
        dispense water
    wait for a random time within delay range
waits for the user to press enter
```

## closed_loop (baseline = false, yoked = false)

```
create a list of tilt types
for i in 0..num_tilts:
    clear pending plexon events
    start tilt i
    for event recieved from plexon within about 200ms:
        if event is a tilt:
            add event to classifier
        if event is a spike:
            add spike to classifier
    classify tilt
    if classification was correct:
        stop tilt and return to level
    if classification was incorrect:
        perform punish tilt
    finish tilt
    wait for after_tilt_delay
    if classification was correct and reward is enabled:
        dispense water
    wait for a random time within delay range
waits for the user to press enter
```

## closed_loop (baseline = false, yoked = true)

```
load list of tilt types from template
for i in 0..num_tilts:
    clear pending plexon events
    start tilt i
    wait about 200ms
    if recorded classification was correct:
        stop tilt and return to level
    if recorded classification was incorrect:
        perform punish tilt
    finish tilt
    wait for after_tilt_delay
    if recorded classification was correct and reward is enabled:
        dispense water
    wait for a random time within delay range
waits for the user to press enter
```

## stim

performs stimulation until enter is pressed

## monitor

waits for enter to be pressed (so recording/live view can be used without tilting)

## bias

records data for a fixed amount of time then exits

# Command line parameters

Some parameters aren't listed in the readme. Run the program with `--help` for a fill list of parameters.

`--config`  
path to hjson config file, see config parameters section

`--labels`  
path to labels config file, see label parameters section

`--bias`  
sets the mode to `bias`

`--overwrite`  
allows overwriting of existing output files

`--monitor`  
sets the mode to `monitor`

`--template-in`  
path to a template file created by a previous run of the program

required in closed loop non baseline, otherwise unused

`--template-out`  
automatically generate a template file at the specified path from the generated events and meta files before exiting

note: if there are a large number of spike events template generation could take a long time

`--loadcell-out`  
path to write ground reaction force data csv to

`--overwrite`  
overwrite exsting output files, if not specified the program will stop if the output file already exists

`--no-start-pulse`  
disable waiting for the plexon start pulse before performing tilts

`--live`  
show live graphs of analog recordings

# Config file

Config parameters that begin with `--` will be added to the passed command line parameters. Setting one of these paramaters to null will pass the command line parameter without a value following it.

The `-` parameter can be set to a list of strings which will be added to the command line parameters.

Other parameters are used as listed below.

## Config parameters

parameters marked with * are required in closed loop mode but do not need to be specified in other modes.  
parameters marked with ** are not required.  

`mode`: Literal['open_loop', 'closed_loop', 'monitor', 'bias']  
see program flow section

`clock_source`: Literal['external', 'internal']  
should normally be set to external

internal uses the internal nidaq clock. externel sets the clock to Dev6/PFI6

`clock_rate`: int  
The rate at which to collect samples in hertz.  
If clock_source is external this should typically be 1000.

`num_tilts`: int  
Number of tilts to perform. This number must be divisible by four. The tilts will be split evenly between the four tilt types.

`tilt_sequence`: Optional[List[str]]  
A fixed sequence of tilts to use instead of generating a randomized sequence. If specified `num_tilts` will be ignored. `sequence_repeat` and `sequence_shuffle` only apply if this parameter is specified.

`sequence_repeat`: int  
The number of times to repeat the tilt sequence.

`sequence_shuffle`: bool  
If true the tilt sequence is randomized. Applies before `sequence_repeat`.

`delay_range`: Tuple[float, float]  
Range of delays between trials in seconds.

`after_tilt_delay`: float  
Delay after tilt completion in seconds.

`baseline`*: Optional[bool]  
If false an input template will be used to classify tilts. If true spikes will be collected without performing classification.

`yoked`*: Optional[bool]  
If true the tilts from the input template will be repeated. If baseline is false the rewards and punish tilts will be repeated. `reward` must be true for rewards to be enabled.

`reward`: bool  
If true a water reward will be given after succesful decoding. If false no water reward will be given. If true the reward is always given with mode == open_loop or baseline == true.

`water_duration`: float  
Duration for which water is dispensed.

`plexon_lib`**: Optional[Literal['plex', 'opx']]  
'plex' uses the `pyplexclientts` library  
'opx' uses the `pyopxclient` library

'opx' should be used with newer plexon systems, 'plex' with older systems

defaults to 'opx'

`stim_enabled`: bool  


`stim_params`: Dict[str, Any]  


# Labels file

## Label parameters

`channels`: Dict[int, List[int]]  
Selects a set of plexon units to be used in the psth template. The parameters of the dict are plexon channels and the values are plexon units within that channel.
