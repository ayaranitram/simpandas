# simpandas
a couple of Pandas DataFrame and Series subclasses extended to work with units and to deal with column names in eclipse simulator output style.

This package is under development and is regularly updated. Backcompatibility is intented to be maintained when possible.

## What Contains This Package
- It is loaded with the network of untis preloaded for distances, area, volume, mass and time conversions defined for SI and Imperial systems according to the definition of each unit, i.e.: _1_foot = 12_inches_.
- Prefixes applied to the basic units, like _k_ to _m_ to make _km_, are loaded as a network of conversions paths allowing the algorith to apply the prefix to any other unit on the same system.
- It provides classes of _units_ useful powered with arithmetich and logic operations to intrincically consider unit conversions when making calculations.

## Requisites
- pandas
- numpy
- matplotlib
- datetime
- unyts

## To install this package:
pip install simpandas