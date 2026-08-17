cd /data/local/tmp/kingfisher || exit 9
P=$1
i=0
while [ $i -lt $P ]; do
  ( taskset 33 ./kernels 2>/dev/null | awk "/^ +100 /{print \$4, \$7}" > /data/local/tmp/k4_$i.out ) &
  i=$((i+1))
done
wait
i=0
while [ $i -lt $P ]; do cat /data/local/tmp/k4_$i.out; i=$((i+1)); done
