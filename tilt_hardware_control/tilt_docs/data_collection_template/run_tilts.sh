
source '/c/Users/moxon/Documents/tilt_hardware_control/setup_data_collection.sh'

tilt --config config.hjson --labels labels.hjson --live --live-secs 30 --no-start-pulse --loadcell-out "tilt_$(dt).csv"

post
