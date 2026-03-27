#!/sh
#automatically finds a USB serial port for slcan device (ie. ttyUSB0)
CANSERIAL=`ls /dev/tty* | grep USB`
echo 'Attempting to attach ' $CANSERIAL 'as slcan device'
#WAS sudo slcan\_attach -f -s4 -o $CANSERIAL  #option -s4 sets bit rate to 125K
sudo slcan\_attach $CANSERIAL  
sudo slcand -S 1000000 $CANSERIAL can0  
sudo ifconfig can0 up 
