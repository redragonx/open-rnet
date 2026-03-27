cansend can0 00c#
cansend can0 00e#0000000000000000
cansend can0 00e#0000000000000000
cansend can0 00e#0000000000000000
cansend can0 00e#0000000000000000
candump -n 1 can0,7b3:7ff
candump -n 1 can0,1f700000:1fff0000
cansend can0 00e#0000000000000000
cansend can0 1f010808#
cansend can0 1f11b190#
cansend can0 1f211e1c#
cansend can0 1f31468a#
cansend can0 1f41dd00#
cansend can0 1f511200#
cansend can0 1f617b00#
cansend can0 1f714500#
sleep 0.04
cansend can0 00e#0000000000000000
sleep 0.04
cansend can0 00e#0000000000000000
sleep 0.04
cansend can0 00e#0000000000000000
sleep 0.04
cansend can0 00e#0000000000000000
sleep 0.04
cansend can0 00e#0000000000000000
sleep 0.04
cansend can0 00e#0000000000000000
candump -n 1 can0,1c0c000:1fffffff #wait for first power indicator
cansend can0 1c240101#

