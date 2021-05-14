
# Dependencies

Windows  
get numpy and Pillow installed somehow

Ubuntu  
`sudo apt-get install python3 python3-pip python3-tk python3-pil.imagetk python3-numpy`

tested with numpy version 1.19.4 but it isn't used heavily so a lot of versions probably work

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

If set to 0 sets the program to perform the home zone exit task.

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
### `Task Type`

Does nothing

---
### `Number of Events`

If set to 0 the homezone exit task will be run, otherwise the joystick pull task will be run

---
### `Task Data Save Dir`

Directory to which log csv files are saved

---
### `Study ID`, `Session ID`, `Animal ID`

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
