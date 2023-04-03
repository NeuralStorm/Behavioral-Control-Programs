
# Dependencies

targets python 3.8

Windows  
get numpy and Pillow installed somehow

Ubuntu  
`sudo apt-get install python3 python3-pip python3-tk python3-pil.imagetk python3-numpy`

tested with numpy version 1.22.4 but it isn't used heavily so a lot of versions probably work

install dependencies
`pip install -r requirements.txt`
`pip install -r requirements_hw.txt`
`pip install -r requirements_histogram.txt`
`pip install -e ../cassifiers`

Optional parameters are considered unspecified if they are ommited, have no values, or have a single empty string value  
The following lines are consided unspecified and will use the default value for `key`
```csv
key
key,

```

# Config

### `reward_thresholds`

example: `low=0'high=4'type=linear'reward_min=0'reward_max=1'cue=bOval`

Each value in the csv is a collection of key value pairs separated by `'`. Each key value pair is of the form `key=value`. Leading and trailing whitespace is removed from keys and values.

The first reward duration where `low < pull duration < high` and `cue` is not set or matches the displayed cue is used.

**General Keys**

`low`, `mid`, `high`: Two of `low` `mid` and `high` must be specified, the last will be computed. Specifies the duration of pull that triggers the reward.

`cue`: If specified only the specified cue will trigger the reward. Must match an entry in images (without the extension).

`type`: Changes the reward scaling. See below for descriptions and additional keys for each type.

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
dBlank.png
bOval.png,bRectangle.png,bStare
```

The files `aBlank.png`, `xBlack.png`, `yPrepare.png` and `zMonkey2.png` are expected to exist in the graphics dir. No files alphabetically before `aBlank.png` or after `xBlack.png` should be placed in the graphics dir.

each image's boxed variant is expected to have the same name with `b` replace with `c` and `d` replaced with `e`. Note that this will replace letters in the shape name, not only the prefix.

---
### `Number of Events`

If set to 0 the homezone exit task will be run, otherwise the joystick pull task will be run

---
### `manual_reward_time`

Duration of water reward when manually triggered with the gui

---
### `Time Out`

A blank screen will be displayed for `Time Out` seconds after the negative image and sound are played. If set to 0 no blank screen will be displayed before the next trial

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
### `Study ID`, `Animal ID`, `Session ID`, `Task Type`

Included in the name of the output csv log file

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
### `post_succesful_pull_delay` (optional)

The delay after a succesful pull before the water reward is dispensed.  
If not specified the delay will be the length of the sound played (1.87s).  
**Note**: If image reward is turned off via the gui this delay will be disabled.

---
### `joystick_channel` (optional)

The channel (direction) of the joystick to use. Default 3.

---
### `no_trials` (optional)

Number of trials to run before stopping. If unspecified or "0" an unlimited number of trials will be performed.

# Histogram generation

## Setup

Install additional dependencies
```sh
pip install -r requirements_histogram.txt
```

## Usage

Example:
```sh
python gen_histogram.py output/TIP_1_001_20220725_180137_Joystick_events.json
```

Example to generate histograms for all events files in output directory, assuming the output directory is `./output`. This requires bash, not cmd.

```sh
python gen_histogram.py ./output/*
```

This can also be done through MonkeyImages_Joystick_Conf.py by selecting the config file

```sh
python MonkeyImages_Joystick_Conf.py gen_histograms
```
