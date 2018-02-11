# ProChange virtual change detection
Virtual change and real concept drift detection via association rule mining in Python

Requires Python 3.5+.

Test with `pytest`.

Auto-format code to PEP8 using `./pyfmt`.

To install required packages:

pip install -r requirements.txt

Note: requires numpy+mkl and scipy which may or not not be available on your platform via pip.

For Windows builds of numpy+mkl, try here:
https://www.lfd.uci.edu/~gohlke/pythonlibs/#numpy

You can run virtual change detection like so:

    python virtualchangedetection.py \
        --input datasets/T1M_DP_V10R20_13.csv \
        --output rules.csv \
        --min-confidence 0.05 \
        --min-support 0.001 \
        --min-lift 1.0 \
        --training-window-size 2500 \
        --drift-algorithm prochange

You can pass "seed", "proseed", "vrchange" and "prochange" with the --drift-algorithm argument to control which drift detection algorithm is used.

Input transaction files must be in CSV format.