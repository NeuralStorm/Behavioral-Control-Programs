
# Installation

targets python 3.11

For installation/usage on a plexon system see [computer_setup.md](https://github.com/NeuralStorm/docs/blob/main/joystick_task/computer_setup.md)

Ubuntu  
`sudo apt-get install python3 python3-pip python3-tk python3-pil.imagetk python3-numpy`

Installation
```
pip install --only-binary :all: --no-binary PyDAQmx -e .[plotting,hw]
```

# Usage

## Running the game

```sh
js-game
```

## Output generation

Example to create output csv, json and histogram png files from the initial json.gz output file
```sh
js-gen-output gen output/TIP_1_001_20220725_180137_Joystick.json.gz
```

Example to create outputs for all json.gz files in the `./output` directory. This requires bash, not cmd.
```sh
js-gen-output --skip-failed gen output/*.json.gz
```

## Histogram generation

Example:
```sh
js-histogram output/TIP_1_001_20220725_180137_Joystick.json.gz
```

Example to generate histograms for all events files in output directory, assuming the output directory is `./output`. This requires bash, not cmd.

```sh
js-histogram --skip-failed ./output/*.json.gz
```

## Online Classification

See [online_classification.md](./documentation/online_classification.md)

# Config

Optional parameters are considered unspecified if they are omitted, have no values, or have a single empty string value  
The following lines are considered unspecified and will use the default value for `parameter`
```csv
parameter
parameter,

```

### `reward_thresholds`

example: `low=0'high=4'type=linear'reward_min=0'reward_max=1'cue=bOval`

Each value in the csv is a collection of parameter value pairs separated by `'`. Each parameter value pair is of the form `parameter=value`. Leading and trailing whitespace is removed from parameters and values.

The first reward duration where `low < pull duration < high` and `cue` is not set or matches the displayed cue is used.

When performing online classification the `mid` value is used.

**General Parameters**

`low`, `mid`, `high`: Two of `low` `mid` and `high` must be specified, the last will be computed. Specifies the duration of pull that triggers the reward.

`cue`: If specified only the specified cue will trigger the reward. Must match an entry in images (without the extension).

`type`: Changes the reward scaling. See below for descriptions and additional parameters for each type.

**Types**

`flat`: A single constant reward duration

* `reward_duration`: Duration of reward

`linear`: Reward duration scales linearly with pull durations distance from `mid`

* `reward_min`: minimum reward duration at `low` or `high`
* `reward_max`: maximum reward duration at `mid`

`trapezoid`: Reward duration scales linearly up to `mid` then is constant

* `reward_min`: minimum reward duration at `low`
* `reward_max`: maximum reward duration above `mid`

---
### `images`

examples:
```
bOval
bOval,bRectangle,bStar
```

Cues should have three versions in the `pending`, `success` and `fail` folders in `joystick_pull/assets/images`  
All three versions should have the same name and end with `.png` extension. The name of the cue used in the config file is the file name without the extension.

Files in the `joystick_pull/assets/pending_only` folder are used as the pending image, only the surrounding box will be shown for the success and fail images.

Files in the `joystick_pull/assets/static` will be used as the pending, success and fail images.

Images will be centered in the canvas and the visible section should fit inside the go cue rectangle which has the inner dimensions 649x435 with the center at 19,16.5 relative to the canvas center.

---
### `Number of Events`

If set to 0 the homezone exit task will be run, otherwise the joystick pull task will be run

---
### `manual_reward_time`

Duration of water reward when manually triggered with the gui

---
### `Time Out`

If trial is not successful a blank screen will be displayed for `Time Out` seconds after the negative image and sound are played. If set to 0 no blank screen will be displayed before the next trial

---
### `Inter Trial Time`

This amount of time must have elapsed after the start of a trial before the trial will begin regardless of wether the hand is in the home zone

---
### `Maximum Time After Sound`

The max amount of time after the go cue that will be waited before the pull is considered a failure

---
### `Task Data Save Dir`

Directory to which log csv files are saved

---
### `Study ID`, `Animal ID`, `Session ID`, `Task Type`, `experimental_group`, `experimental_condition`

Included in the name of the output csv log file. Defaults to "`NOTSET`".

---
### `Enable Blooper Noise`

if set to "TRUE" a noise will be played after an unsuccesful trial (the noise after a succesful trial can't be disabled)

---
### `Pre Discriminatory Stimulus Min delta t1`, `Pre Discriminatory Stimulus Max delta t1`

A number in the range [`Pre Discriminatory Stimulus Min delta t1`, `Pre Discriminatory Stimulus Max delta t1`] will be selected each trial for the delay between the hand entering the home zone and a shape being shown on the screen. Min and max can be set to the same value to have a fixed delay.

---
### `Pre Go Cue Min delta t2`, `Pre Go Cue Max delta t2`

A number in the range [`Pre Go Cue Min delta t2`, `Pre Go Cue Max delta t2`] will be selected each trial for the delay between a shape being shown and the go cue being shown. Min and max can be set to the same value to have a fixed delay.

---
### `post_successful_pull_delay` (optional)

The delay after a successful pull before the water reward is dispensed.  
If not specified the delay will be the length of the sound played (1.87s).  

---
### `joystick_channel` (optional)

The channel (direction) of the joystick to use. Default 3.

---
### `no_trials` (optional)

Number of trials to run before stopping. If unspecified or "0" an unlimited number of trials will be performed.

---
### `template` (optional)

The path of the classifier template file to load. If this parameter is specified classification will be enabled.

---
### `classify_wait_timeout` (optional)

Amount of time, based on the computer's local time, to wait before failing classification.

If not specified the program will wait an indefinite amount of time for the event to occur.

# Environment Variables

For environment variables marked [flag] any value that is set and not an empty string will enable the functionality.  
For example (bash)
```bash
export record_events='1'
```

---
### `config_path`

use config file at path instead of showing gui file chooser

---
### `event_source`

set to `plexon` or `ability` to collect events from an external system

---
### `out_file_name`

overrides normal file name generation and uses a fixed value instead

---
### `photodiode_flash_duration`

photodiode marker flash duration in seconds, set to 0 to disable the photodiode marker flash  
default: 0.018

---
### `photodiode`

photodiode settings, hjson string

`channel`: analog channel that the photodiode is on  
`threshold`:  
thresholds for photodiode signal in volts  
falling edges must fall below the first value for the signal to be considered low  
rising edges must rise above the second value for the signal to be considered high  
`min_pulse_width`: the number of samples the signal must be high for the photodiode to be considered on  
`edge_offset`:  
offset of the generated timestamp when the photodiode becomes on  
this should probably be `min_pulse_width` / -1000 to get the timestamp when the signal initially went high

Example (bash)
```bash
export photodiode='{
    channel: 8
    threshold: [0.005, 0.02]
    min_pulse_width: 4
    edge_offset: -0.004
}'
```
---
### `disable_record_events` [flag]

Disable recording of classification events and spikes.

---
### `record_analog`

Enable recording of analog channels, hjson string

Keys are the names used in the saved data, values are the channels recorded from.

The `photodiode` channel can be set to `auto` to use the channel configured with the photodiode environment variable.

The `joystick` channel can be set to `auto` to use the channel configured in the config file.

Example (bash)
```bash
export record_analog='{
    photodiode: auto
    go_cue_photodiode: 3
}'
```

The default is
```json
{
    "photodiode": "auto",
    "joystick": "auto"
}
```

---
### `classifier_debug` [flag]

generates fake spike events and classification events for simulated interactions

---
### `simulate_photodiode` [flag]

generates fake photodiode events

---
### `no_git` [flag]

disable fetching and saving of git status

---
### `no_print_stats` [flag]

disable calculation and printing of histogram info in the console

---
### `trace`, `log` [flag]

enables verbose logging (trace is more verbose than log)

---
### `no_wait_for_start` [flag]

disables waiting for a recording start event from plexon

---
### `no_info_view` [flag]

disable the info view and associated calculations

---
### `hide_buttons` [flag]

hide ui buttons

---
### `layout_debug` [flag]

color different ui elements different colors to aid debugging of the ui layout
