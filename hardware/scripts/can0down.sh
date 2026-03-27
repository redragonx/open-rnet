#!/bin/sh
#bring can0 down and kill slcan daemon
sudo ifconfig can0 down  
sudo killall slcand  
