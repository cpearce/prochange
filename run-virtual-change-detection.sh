python virtualchangedetection.py \
   --input datasets/T1M_DP_V10R20_13.csv \
   --output rules.csv \
   --min-confidence 0.05 \
   --min-support 0.001 \
   --min-lift 1.0 \
   --training-window-size 2500 \
   --drift-algorithm prochange