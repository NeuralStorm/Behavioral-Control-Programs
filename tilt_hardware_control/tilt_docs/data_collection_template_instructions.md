
create a copy of the `data_collection_template` directory, the copy should go somewhere outside the `tilt_hardware_control` directory  
the template directory can be found in the tilt_docs directory which is pinned to Quick Access

modify `config.hjson`

`.sh` files can be run in git bash by double clicking them

`run_tilts.sh` performs tilts and collects data from the grf sensors, displays the live graphs  
`run_bias.sh` collects a bias file  
`run_monitor.sh` displays the live graphs and collects data without tilting
