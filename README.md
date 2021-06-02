# datafiletoolbox
A set of classes and utilities to read different simulation output files, text files and excel file in certain formats.
In order to read eclipse style binaries this utility relies on libecl from equinor: https://github.com/equinor/ecl

datafiletoolbox can also read eclipse style input data deck, but this feature is not fully developed and is still a prototype. 
It can be easly read include files of properties exported from Petrel to Eclipse and return a DataFrame with the data read from the file.

It takes care of the units of the data loaded and is able to convert into other units.
In order to keep track of the units, a subclass of Pandas, is used to return the results.

## load data
The easiest way to load data is using the function loadSimulationResults
from datafiletoolbox import loadSimulationResults
data = loadSimulationResults( *path_to_file* )

## get_data
To extract data from the loaded files the instances works in analogous way to the Python dictionaries and Pandas DataFrames. 
We can request a single Series using [ *key_to_extract* ] or DataFrames using [[ *key_to_extract* ]].
The instance can also be called using ( *key_to_extract* ) and in this case will return a Numpy array.

### keys of VIP simulation results
The data from a VIP simulation can be accessed using regular eclipse nomenclature, like 'FOPT' meaning 'Qo' of 'ROOT' or 'WGPR:WELL1' meaning 'Qg' of 'WELL1'.

### keys, wells, groups, regions
The properties **.keys**, **.wells**, **.groups**, **.regions** contains tuples with their corresponding list of values available in the loaded data. 
The method **.find_Keys()** can be used to find keys related to any well, group, region, attribute or pattern (using ? * ...)

### generic keys
The **key** does not need to be exact, it can be:
- a general property, like 'WOPR', and the class will return all the vector for this key
- the name of a well, region or group, like 'WELL1', and the class will return all the vector for that key
- it can contain wildcards, like 'W?PR' or 'WELL*'

### changing the index of the returned DataFrames
The default *index* is defined automatically based on the available data, usually is the 'TIME' vector or the 'DATE' vector.
To change the index use the __.set_index( *key* )__ method. It can be any *key* in the data.

## plotting
To make a plot from an instance of loaded data, simply use the .plot( *keys* ) method and a matplotlib plot will be generated setting the color of the lines according to the fluid or data plotted.
### X axis
By default, the X axis of the plot will be the *index* set to the instance.
### comparing different results from different simulations
To compare the results of different simulations, simply pass the variable representing the instance of the other simulation to the __.plot()__ method. The class will extract the data from both instances of data, convert the units of the other instances if required and display the plot:

assume data0 is an eclipse binary result and data1 is a VIP simulation results
data0.plot('FOPR',data1)
will get the data from both results (converting the key from ECL style to VIP style to extract the data), convert units of data1 to corresponding units of data0 and show the plot.

## many more functions are available, not detailed in this readme. A more detailed tutorial will be available sometime, in the meanwhile, please contact the author <martincarlos.araya@cepsa.com> for further details.
