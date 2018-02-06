python virtualchangedetection.py \
   --input datasets/poker-hand-training-true.data \
   --output poker.rules \
   --min-confidence 0.05 \
   --min-support 0.05 \
   --min-lift 1.0 \
   --training-window-size 2500 \
   --drift-algorithm seed