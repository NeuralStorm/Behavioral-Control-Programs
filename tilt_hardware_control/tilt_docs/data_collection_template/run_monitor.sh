
source '/c/Users/moxon/Documents/tilt_hardware_control/setup_data_collection.sh'

tilt --config config.hjson --monitor --live --live-secs 30 --loadcell-out "notilt_$(dt).csv"

post
