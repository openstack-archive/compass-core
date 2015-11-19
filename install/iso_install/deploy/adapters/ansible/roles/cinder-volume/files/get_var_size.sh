size=`df /var | awk '$3 ~ /[0-9]+/ { print $4 }'`;
if [[ $size -gt 2000000000 ]]; then
  echo -n 2000000000000;
else
  echo -n $((size * 1000 / 512 * 512));
fi
