
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
