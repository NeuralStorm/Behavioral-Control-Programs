
## list of input and output files
```
Input Files
Configuration CSV File: This file contains various settings and parameters that dictate the behavior of the experiment. It includes settings like reward_thresholds, images, and various timing and behavioral parameters.
Template File (JSON):The template file is in Json format

Output Files
Data Files (.json.gz): The output from the experimental sessions is generated in the .json.gz format. This compressed JSON format is commonly used for efficiently storing and transferring large amounts of structured data. The content of these files includes:
Events:
Analog Signals:
Spike Times:
Debug Information:
```

## Question: What is Output Generation and Histogram Generation about? Aren't these files automatically created at the end of the game play?
Answer: Output Generation and Histogram Generation are processes for converting raw data collected during gameplay into usable formats (CSV, JSON) and visual representations (histograms), respectively. These files are not automatically created at the end of gameplay; you need to run additional commands specified in the README to process the raw data into these formats.

## Question: What does --skip-failed mean in the context of these commands?
Answer: The --skip-failed option in the commands is used to instruct the program to ignore or skip over any files that encounter issues (like being corrupted or incomplete) during the output or histogram generation process.

## Question: What does the file path ./output/*.json.gz represent, and what is a .gz file?
Answer: The file path ./output/*.json.gz represents wild card search  ./output/ is the directory containing the output files, and *.json.gz matches any file in that directory with a .json.gz extension. A .gz file is a compressed file format, similar to .zip, often used to reduce the size of large data files. 

## Question 4: What does 'must match an entry in images (without extension)' mean?
Answer: This means that the name used in the configuration for a cue should exactly match the filename of an image used as a cue in the program, but the file extension (like .png) should not be included in the configuration. For example, if the image file is bOval.png, you would refer to it in the configuration as just bOval.


## Question 5: What is the 'cue' about? How does the cue trigger the reward?
Answer: A cue in this context is a visual stimulus presented to the subject during the game, such as an image. The cue triggers a reward based on the subject’s correct response to it. If the configuration specifies a cue, the program understands that the reward should only be given if the subject responds appropriately to that specific cue. This mechanism is a part of the behavioral experiment setup to assess and reinforce specific responses to stimuli.

## 6. What is an environmental variable and how do you use them?

https://en.wikipedia.org/wiki/Environment_variable

## I see the list but I don't know what a 'config file at path'.

a config file at path is a file containing the config as explained in the readme which is present in the computer's filesystem at the specified path

## I didn't know we had any gui's... I'm super confused

the program has a gui, by default a gui file selection dialogue is shown

## 7. can the default for record_events always be yes or on ?

`record_events` has been replaced with `disable_record_events` and the default is to record spikes and classification events

## 8. record_analog??? 'can be set to auto to use channel configured in config file' No, the information always comes from the config file. We talked about this multiple times. there is no ability for the average user to get information into any file except through the config. If Ryan wants a backdoor, that is fine but it is NOT to be any manual at this time.

unclear if this is asking this environment variable to not be documented

## 9. same with all of the debugging flags - please move them out to a separate section and, here, no problem if these are not called from the config file but they need to be away from everything else as most users can not get involved in this, it adds a layer of complexity we do not need at this time.

reorganization of the documentation can be considered
