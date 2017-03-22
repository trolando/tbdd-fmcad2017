TBDD experiments
==================
This repository hosts the source code and logfiles of the experimental section in the paper on Tagged BDDs submitted to FMCAD 2017.

You can contact the main author of Sylvan at <tom.vandijk@jku.at>.

Sylvan source code: https://github.com/trolando/sylvan  
LTSmin source code: https://github.com/trolando/ltsmin  
DiVinE: https://github.com/utwente-fmt/divine2

Information on the experiments are found in the submitted paper.

Files
=====
The `expfw.py` script provides the framework for experiments, the `exp.py` script runs the experiments

Use `exp.py` with either parameter `run` or `report` to run the experiments or to generate a report of the results.

Reproducing BEEM benchmarks (DVE)
=================================
Use DiVinE and the compile script in the `dve` subdirectory to generate dve2C files.

Use the `tbdd` branch of Sylvan and the `tbdd` branch of LTSmin. Compile and install Sylvan and LTSmin and then the `exp.py` script runs the benchmarks.
