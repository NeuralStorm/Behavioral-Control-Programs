
# Setup

Install dependencies  
`pip install -r requirements.txt`

If using live graph view  
`pip install pyside6`  
if installation fails use  
`pip install pyside2==5.15.2`  

# Usage

Example command line calls
```bash
python main.py --config example_config.hjson --template-out x.json
python main.py --config example_config.hjson --template-out x_2.json --template-in x.json
python main.py --config example_config.hjson --template-out x_2.json --template-in x.json --loadcell-out grf_data.csv
```

## Usage example

### Open loop

Make a copy of example_config.hjson, ensure `mode` is set to open_loop. Set `num_tilts` and `delay_range` to the desired values. `baseline`, `sham`, `reward` and `channels` can be ignored or removed from the config file.

Run the script (how python in envoked will vary depending on system configuration)
```
python main.py --config your_config.hjson --loadcell-out grf_data.csv
```
This will read setting from `your_config.hjson` and write recorded grf data to `grf_data.csv`. Note that if `grf_data.csv` already exists it will be overwritten.

The program will run through the specified number of tilts then exit.

---
### Closed loop, initial run

Make a copy of example_config.hjson, set `mode` to closed_loop, `baseline` to true and `sham` to false. Set `num_tilts`, `delay_range`, and `channels` to the desired values. `reward` is not used.

Run the script (how python in envoked will vary depending on system configuration)
```
python main.py --config your_config.hjson --template-out template_a.json --loadcell-out grf_data.csv
```
This will read settings from `your_config.hjson` and write recorded grf data to `grf_data.csv`. Note that if `grf_data.csv` already exists it will be overwritten. PSTH template data and a record of the run will be written to `template_a.json`.

Make sure to use enter and not ctrl-c if you need to pause the program.

The program will perform tilts and record the psth templates.

---
### Closed loop, after initial run

Make a copy of the config used for the initial run and change `baseline` to false.

Run the script (how python in envoked will vary depending on system configuration)
```
python main.py --config your_other_config.hjson --template-in template_a.json --template-out template_b.json --loadcell-out grf_data.csv
```
This will read settings from `your_other_config.hjson` and write recorded grf data to `grf_data.csv`. Note that if `grf_data.csv` already exists it will be overwritten. PSTH templates are loaded from `template_a.json`. PSTH template data and a record of the run will be written to `template_b.json`.

The program will perform tilts and attempt to classify the tilt type based on templates from `template_a.json` and perform punish/reward actions based on if the classification was correct. It will also record a new set of templates.

---
### Live view

Add the `--live` parameter to enable the live view.
```
python main.py --config your_config.hjson --monitor --live
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

### open loop

ctrl-c can be pressed to immediatly stop the current tilt. enter will resume the program, ctrl-c again will exit the program

### closed loop

pressing enter will pause the program at the end of the current tilt. pressing enter will resume the program, pressing q then enter will exit the program

## Notes on clocks

Plexon outputs a 40khz clock signal. This is downsampled by a hardware downsampler to 1250hz and sent to Dev6/PFI6.

Using plexon's clock signal instead of the internal nidaq clock means, given one known shared event (such as the start pulse), all the neural and grf data can be correlated in time. Without using a shared clock the two clocks will experience a different amount of drift and diverge over time.

clock_source should always be set to external in normal use.

## Ground reaction forces recording

Grf data is recorded concurrently with the rest of the program.

The grf data csv has the following columns

```
rhl_fx = right hindlimb force in the x axis
lhl_ty = left hindlimb torque in the y axis
fl_fz = forelimb force in the z axis
```

Note: The analysis pipeline and these docs currently refers to the side with two sensors as the hindlimbs but they could be the forelimbs if the animal is placed on the platform facing the other direction.

```
Dev6/ai18: rhl_fx
Dev6/ai19: rhl_fy
Dev6/ai20: rhl_fz
Dev6/ai21: rhl_tx
Dev6/ai22: rhl_ty
Dev6/ai23: rhl_tz
Dev6/ai32: lhl_fx
Dev6/ai33: lhl_fy
Dev6/ai34: lhl_fz
Dev6/ai35: lhl_tx
Dev6/ai36: lhl_ty
Dev6/ai37: lhl_tz
Dev6/ai38: fl_fx
Dev6/ai39: fl_fy
Dev6/ai48: fl_fz
Dev6/ai49: fl_tx
Dev6/ai50: fl_ty
Dev6/ai51: fl_tz
Strobe: ttl pulse indicating start of tilt
Start: ttl pulse indicating start of plexon recording
Inclinometer: Inclinometer
Timestamp: Timestamp (generated based on 
```

# Arguments

Some arguments aren't listed in the readme. Run the program with `--help` for a fill list of arguments.

`--template-in`

path to a template file created by a previous run of the program

required in open loop non baseline, otherwise unused

`--template-out`

path to write template file to

optional in closed loop, otherwise unused

`--loadcell-out`

path to write ground reaction force data csv to

`--labels`

path to an hjson labels file. `channels` will be loaded from the labels file instead of the config file

`--config`

path to hjson config file, see config keys section

# Program flow

## open loop

```
create a list of tilt types
wait for start pulse
for i in 0..num_tilts:
    perform tilt i
    if reward enabled:
        dispense water
    wait for a random time within delay range
```

## closed loop baseline

```
create a list of tilt types
wait for start pulse
for i in 0..num_tilts:
    clear pending plexon events
    start tilt i
    loop a:
        for `event` recieved from plexon:
            if event is a tilt:
                add event to psth
            if event is a spike:
                add spike to psth
                if time since tilt > post time:
                    break a
    finish tilt
    wait for a random time within delay range
```

## closed loop (baseline = false, sham = false)

```
create a list of tilt types
for i in 0..num_tilts:
    clear pending plexon events
    start tilt i
    loop a:
        for `event` recieved from plexon:
            if event is a tilt:
                add event to psth
            if event is a spike:
                add spike to psth
                if time since tilt > post time:
                    break a
    classify tilt
    if classification was correct and reward is enabled:
        dispense water
    if classification was incorrect:
        perform punish tilt
    finish tilt
    wait for a random time within delay range
```

## closed loop sham (baseline = false)

```
load list of tilt types from template
for i in 0..num_tilts:
    clear pending plexon events
    start tilt i
    loop a:
        for `event` recieved from plexon:
            if event is a tilt:
                add event to psth
            if event is a spike:
                add spike to psth
                if time since tilt > post time:
                    break a
    classify tilt
    if classification recorded for tilt i in the template was correct and reward is enabled:
        dispense water
    if classification recorded for tilt i in the template was incorrect:
        perform punish tilt
    finish tilt
    wait for a random time within delay range
```

## monitor

waits for enter to be pressed (so recording/live view can be used)

# Config file

Keys that begin with `--` will be added to the passed command line parameters. The `_` key can be set to a list of strings which will be added to the command line arguments.

Other keys are used as listed below.

# Config keys

`mode`: Literal['open_loop', 'closed_loop', 'monitor']

see program flow section

`clock_source`: Literal['external', 'internal']

should normally be set to external

internal uses the internal nidaq clock. externel sets the clock to Dev6/PFI6

Dev6/PFI6 should be connected to the downsampled plexon clock

`clock_rate`: int

The rate at which to collect samples in hertz.
If clock_source is external this should probably be 1250.

`num_tilts`: int

Number of tilts to perform. This number must be divisible by 4. The tilts will be split evenly between tilt types 1, 2, 3 and 4.

`delay_range`: Tuple[float, float]

Range of delays between tilts is seconds.

`baseline`: Optional[bool]

Only used when mode == closed loop. If false an input template will be used to classify tilts. If true a template will be generated without performing classification.

`sham`: Optional[bool]

If true the tilts from the input template will be repeated. If baseline is false the rewards and punish tilts will be repeated. reward must be true for rewards to be enabled.

`reward`: Optional[bool]

If true a water reward will be given after succesful decoding. If false no water reward will be given.

`channels`: Dict[int, List[int]]

Maps plexon units to event types where that unit should be used in psth generation.
