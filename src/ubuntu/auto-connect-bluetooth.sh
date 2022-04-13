#!/bin/bash

sudo bluetoothctl trust $BLUETOOTH_AUTO_CONNECT_MAC

while true; do
  sleep 1
  OUTPUT=$(bluetoothctl connect $BLUETOOTH_AUTO_CONNECT_MAC)

  if [[ "$OUTPUT" =~ .*"Connection successful".* ]]; then
    echo "Connection successful"
    break
  fi
  wait # for sleep
done
