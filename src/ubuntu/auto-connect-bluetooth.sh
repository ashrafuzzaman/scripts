#!/bin/bash

while true; do
  sleep 1
  OUTPUT=$(sudo bluetoothctl connect $BLUETOOTH_AUTO_CONNECT_MAC)

  if [[ "$OUTPUT" =~ .*"Connection successful".* ]]; then
    echo "Connection successful"
    break
  fi
  wait # for sleep
done
