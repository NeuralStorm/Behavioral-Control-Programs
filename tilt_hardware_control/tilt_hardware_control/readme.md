# Tilt Hardware Control

## Important Note

The Moxon Neurorobotics Laboratory maintains a [Codebase Master Document](https://ucdavis.box.com/s/icsjygmi2bkcv1275xskigibiewahd3p) that introduces users to key concepts that are helpful for properly understanding, installing, and using this program. It is highly recommended that new users and lab members review the document in its entirety before proceeding.


## Content Guide

- **[Summary](#Summary)**: Explanation of program purpose, its required inputs, and its expected outputs.
- **[Pipeline](#Pipeline)**: Ordered list of what the program does when.
- **[Usage Guide](#Usage-Guide)**: How to use the program.
    - **[Installation](#Installation)**: How to install the program.
    - **[Procedural Notes](#procedural-notes)**: Guidance on procedural standards.
    - **[Config File](#Config-File)**: Explanation of the config file and its contents.
    - **[Command Line](#command-line)**: Breakdown of the command line and its arguments.
- **[Examples](#Examples)**: How to use the program.
    - **[Open Loop](#open-loop)**
    - **[Closed Loop](#closed-loop)**

## <a name="Summary">Summary</a>

This program contains scripts for any experiments and tests that require programming any of the motors controlling the rodent tilt platform.

MONA accepts the following files, **which must be provided by the user**:
|Terminology          |Contents                                                |Accepted File Formats|
|---------------------|--------------------------------------------------------|---------------------|
|Config file          |Contains modifiable parameters and arguments.           |`.hjson`    |
|Label file          |Alternative file through which to provide channels.           |`.hjson`    |

Once properly run, the program should follow the instructions listed in the configuration file. If requested, it should also return a template `.json` file.

## <a name="Pipeline">Pipeline</a>

The program is divided into a number of modular components that each handle a different part of the greater pipeline, and which can each be run either on their own or through a batch process.

**Open Loop**
1. Create list of tilt types.
2. Wait for start pulse.
3. For each tilt:
    1. Perform the tilt.
    2. If rewards are enabled, dispense water.
    3. Wait for a random amount of time that falls within the delay range.

**Closed Loop** (Baseline = True, Sham = False)
1. Create list of tilt types.
2. Wait for start pulse.
3. For each tilt:
    1. Clear any pending Plexon events.
    2. Begin the tilt.
    3. For each event received from the Plexon machine:
        1. Add it to the PSTH
        2. If the event is a spike and the time since the tilt > post time, break this Plexon loop.
    4. Finish the tilt.
    5. Wait for a random amount of time that falls within the delay range.

**Closed Loop** (Baseline = False, Sham = False)
1. Create list of tilt types.
2. For each tilt:
    1. Clear any pending Plexon events.
    2. Begin the tilt.
    3. For each event received from the Plexon machine:
        1. Add it to the PSTH
        2. If the event is a spike and the time since the tilt > post time, break this Plexon loop.
    3. Classify the tilt.
        a. If the classification was correct and the reward is enabled, dispense water.
        b. If the classification was incorrect, perform a punishment tilt.
    4. Finish the tilt.
    5. Wait for a random amount of time that falls within the delay range.

**Closed Loop** (Baseline = False, Sham = True)
1. Create list of tilt types from template.
2. For each tilt:
    1. Clear any pending Plexon events.
    2. Begin the tilt.
    3. For each event received from the Plexon machine:
        1. Add it to the PSTH
        2. If the event is a spike and the time since the tilt > post time, break this Plexon loop.
    3. Classify the tilt.
        1. If the classification was correct and the reward is enabled, dispense water. If the classification was incorrect, perform a punishment tilt.
    4. Finish the tilt.
    5. Wait for a random amount of time that falls within the delay range.


## <a name="Usage-Guide">Usage Guide</a>


### <a name="Installation">Installation</a>

To install this program, follow the steps outlined in the Git tutorial within the [Codebase Master Document](https://ucdavis.box.com/s/icsjygmi2bkcv1275xskigibiewahd3p). If you're using live graph view, please be sure to use `pip install pyside6`. Opt for `pip install pyside2==5.15.2` if the installation fails.


### <a name="procedural-notes">Procedural Notes</a>

- **Internal versus External Clocks**
    The plexon machine natively outputs a 40 kHz clock signal, which is downsampled to 1250 Hz using hardware solutions and then sent to the `Dev6/PFI6` channel. Using this clock signal allows the neural and behavioral data to by synced across time for any given shared event (such as, say, a start pulse).
    
    Opting for the internal nidaq clock complicates this matter and risks unsynced data, which can cause downstream issues when neural and behavioral data need to be reconciled with one another. For this reason, `clock_source` should generally be set to `external` during normal use.
    
- **Recordings of Ground Reaction Forces**
    The Ground Reaction Force data recording runs concurrently with the rest of the program. Keeping in mind the naming conventions `rhl`/`lhl`/`fl` = `right hind limb`/`left hind limb`/`front limb` and`fx`/`ty`/`fz` = `Force along the X axis`/`Torque along the Y axis`/`Force along the Z axis`, the GRF output `.csv` will contain the following columns and their associated meanings:
    
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
Timestamp: Timestamp
```

### <a name="Config File">Config File</a>

The configuration file defines a number of parameters that control the program's behavior. The keys found within can be qualified with a `--` prefix (e.g. `--delay_range (2,6)`) to be added to the command line. The `_` key can also be set to a list of strings which are also added to the command line.

Beyond those, these are the configuration keys the program will expect:
|Parameter|Description|Format|
|----------------------|-------------|:-------:|
|`mode`|Defines which mode the program runs in.|`open_loop`/`closed_loop`/`monitor`|
|`clock_source`|Controls which clock the program ought to use. [^clockn]|`internal`/`external`|
|`clock_rate`|Rate at which samples are collected, in hertz. [^raten]|`Int`|
|`num_tilts`|# of tilts to perform, must be divisible by 4.|`Int`|
|`delay_range`|The range of possible delays between tilts, in seconds.|`(Float, Float)`|
|`baseline`|Defines the program's handling of templates. [^bslnex]|`True`/`False|
|`sham`|Defines the program's handling of repetitions. [^shamex]|`True`/`False`|
|`reward`|Toggles rewards.|`True`/`False`|
|`channels`|Maps Plexon units to event types where they should be used in PSTH generation.|`Dict[Int, List[Int]]`

[^clockn]: If set to `internal`, the program will use the *internal* nidaq clock. If set to `external`, the program will set the clock to the `Dev6/PFI6` channel, which should itself be connected to the downsampled Plexon clock.
[^raten]: If `clock_source` is set to external, `clock_rate` should generally be set to 1250.
[^bslnex]: `baseline` is only used when `mode` is set to `closed_loop`. If `baseline` is set to `False`, the input template provided by the user will be used to classify tilts. If it is set to `True`, the template will be generated without performing classification.
[^shamex]: If `sham` is set to `True`, the tilts from the input template will be repeated. If `baseline` is also false, the rewards and punishment tilts will also be repeated, though rewards will only be enabled if `reward` is set to `True`.

### <a name="command-line">Command Line</a>

The program is run by calling `python main.py`, with the following arguments being passable:

|Argument|Description|Required?|
|----------------------|-------------|:-------:|
|`--help`|Lists all arguments.|❎|
|`--template-in`|Denotes the path to a template file created by a previous run of this program.|✅[^onop]
|`--template-out`|Denotes the path in which a template file should be saved.|❎[^oncl]
|`--loadcell-out`|Denotes the path in which the GRF data csv should be saved.|✅
|`--labels`|Denotes the path to a user-provided `.hjson` labels file.|❎[^onlab]
|`--config`|Denotes the path to a user-provided `.hjson` config file.|✅
|`--live`|Toggles live view.|❎

[^onop]: Only required in open loop, non-baseline runs.
[^oncl]: Optional in close loop run, not used otherwise.
[^onlab]: If specified, `channels` will be loaded from the labels file rather than the config file.

A complete, functional command line call would thus look like this:
```
python main.py --config example_config.hjson --template-out x.json
```
Which would cause the program to follow the instructions laid out in `example_config.hjson` and save the template to `x.json`.

## <a name="Examples">Examples</a>


### <a name="open-loop">Open Loop</a>

To quickly run an open loop experiment, create a copy of `example_config.hjson` and edit the file such that `mode` is set to `open_loop`. Ensure that `num_tilts` and `delay_range` to appropriate values. `baseline`, `sham`, `reward`, and `channels` cann all be ignored, as the program does not make use of these keys when set to open loop mode.

The program would then be run using this command line call:
```
python main.py --config your_config.hjson --loadcell-out grf_data.csv
```

The program will then read `your_config.hjson`, read in the settings listed within, and then write any GRF data recorded to `grf_data.csv`. **Note that this file will be overwritten if left in the same directory during subsequent runs.** The program will proceed through the specified number of tilts (users can press CTRL + C to pause and unpause the current tilt) and then exit.


### <a name="closed-loop">Closed Loop</a>

To quickly run a closed loop experiment, create a copy of `example_config.hjson` and edit the file such that `mode` is set to `closed_loop`. Since this is the first closed loop run of the program, set `baseline` to `True` and `sham` to `False`. Users should set `num_tilts`, `delay_range`, and `channels` to appropriate values. `reward` will not be used.

The program would then be run using this command line call:
```
python main.py --config your_config.hjson --template-out template_a.json --loadcell-out grf_data.csv
```

The program will then read `your_config.hjson`, read in the settings listed within, and then write any GRF data recorded to `grf_data.csv`. **Note that this file will be overwritten if left in the same directory during subsequent runs.** PSTH template data and a recording of the run will be written to `template_a.json`. The program will proceed through the specified number of tilts (users can press Enter to pause and unpause the program at the end of the current tilt) and then exit (users can also press Q to exit prematurely).

Now that the program has been run in closed loop mode and the run saved to a template file, we can edit the config file to set `baseline` to `False` and use this command line call:
```
python main.py --config your_other_config.hjson --template-in template_a.json --template-out template_b.json --loadcell-out grf_data.csv
```

The program will again read `your_config.hjson`, again write any GRF data recorded to `grf_data.csv`, but this time, the PSTH templates will be loaded from `template_a.json`. The program will then perform all of the tilts and attempt to classify the tilt type based on the templates from `template_a.json`, as well as perform punish/reward actions based on whether the classifications were correct. The program will also record a new set of templates and save it to `template_b.json`.