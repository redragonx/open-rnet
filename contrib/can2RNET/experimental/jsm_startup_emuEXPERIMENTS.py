#!/python3
# joystick based on: https://www.kernel.org/doc/Documentation/input/joystick-api.txt

import socket, sys, os, struct, array, time
from fcntl import ioctl
#import select
import threading
import select
from candump_to_socketcan_defs import *


debug = False

def dec2hex(dec,hexlen):  #convert dec to hex with leading 0s and no '0x' 
    h=hex(int(dec))[2:]
    l=len(h)
    if h[l-1]=="L":
        l-=1  #strip the 'L' that python int sticks on
    if h[l-2]=="x":
        h= '0'+hex(int(dec))[1:]
    return ('0'*hexlen+h)[l:l+hexlen]
                            
def send_joystick_canframe(s,joy_id, start_delay):
        global joyx
        global joyy
        mintime = .01
        joy_socketcanframe = bytearray(build_cansend_frame(joy_id+'#0000'))
        sleep(start_delay)
        nexttime = time() + mintime
        while True:
                joy_socketcanframe[8] = joyx
                joy_socketcanframe[9] = joyy
                s.send(joy_socketcanframe)       
                nexttime += mintime
                if time() < nexttime:
                    sleep(nexttime - time())
                else:
                    nexttime += mintime
                    
def send_joystick_syncronous_canframe(joy_id, resend_delay):
        cansocket = socket.socket(socket.AF_CAN, socket.SOCK_RAW, socket.CAN_RAW)
        cansocket.bind(('can0',))
        time.sleep(resend_delay)
        joy_socketcan_fmt = build_cansend_frame(joy_id+"#0000")
        while True:
            cf, addr = cansocket.recvfrom(16)
            if cf == joy_socketcan_fmt:
                time.sleep(resend_delay)
                send_cansend_frame(cansocket,joy_id+'#'+dec2hex(joyx,2)+dec2hex(joyy,2))  

def wait_joystickframe(cansocket):
    frameid = ''
    while frameid[0:3] != '020':  #just look for joystick frame ID (no extended frame)
        cf, addr = cansocket.recvfrom(16)
        candump_frame = dissect_candump_frame(cf)
        frameid = candump_frame.split('#')[0]
    return(frameid)

def induce_JSM_error(cansocket):
    for i in range(0,3):
        send_cansend_frame(cansocket,'0c000000#')

"""
def kill_proc_tree(pid, including_parent = True):
    parent = psutil.Process(pid)
    for child in parent.get_children(recursive=True):
        child.kill()
    if including_parent:
        parent.kill()

def terminate():
    me = os.getpid()
    kill_proc_tree(me)
"""
def send_781s_vs2(s): #JSMserial_num = '08901c8a'
    cansend(s,'781#2080000011000000')
    canwait(s,'790:7ff')
    cansend(s,'781#4080000000000000')
    canwait(s,'790:7ff')
    cansend(s,'781#2081000006000100')
    canwait(s,'790:7ff')
    cansend(s,'781#408F000000000000')
    canwait(s,'790:7ff')
    cansend(s,'781#2081000002000000')
    canwait(s,'790:7ff')
    cansend(s,'781#408F000000000000')
    canwait(s,'790:7ff')
    cansend(s,'781#2081000008000100')
    canwait(s,'790:7ff')
    cansend(s,'781#408F000000000000')
    canwait(s,'790:7ff')
    cansend(s,'781#2081000013000100')
    canwait(s,'790:7ff')
    cansend(s,'781#408F000000000000')
    canwait(s,'790:7ff')
    cansend(s,'781#208100000E000100')
    canwait(s,'790:7ff')
    cansend(s,'781#408F000000000000')
    canwait(s,'790:7ff')
    cansend(s,'781#2081000018000100')
    canwait(s,'790:7ff')
    cansend(s,'781#408F000000000000')
    canwait(s,'790:7ff')
    cansend(s,'781#2080000000000000')
    canwait(s,'790:7ff')
    cansend(s,'781#4040000000000000')
    canwait(s,'790:7ff')
    cansend(s,'781#4050000000000000')
    canwait(s,'790:7ff')
    
def send_781s_vs1(s):
        cansend(s,'781#2080000011000000')
        canwait(s,'790:7FF')
        cansend(s,'781#4080000000000000')
        canwait(s,'790:7FF')
        cansend(s,'781#2081000006000100')
        canwait(s,'790:7ff')
        cansend(s,'781#408f000000000000')
        canwait(s,'790:7ff')
        cansend(s,'781#2081000002000000')
        canwait(s,'790:7ff')
        cansend(s,'781#408f000000000000')
        canwait(s,'790:7ff')
        cansend(s,'781#2081000008000100')
        canwait(s,'790:7ff')
        cansend(s,'781#408f000000000000')
        canwait(s,'790:7ff')
        cansend(s,'781#2081000013000100')
        canwait(s,'790:7ff')
        cansend(s,'781#408f000000000000')
        canwait(s,'790:7ff')
        cansend(s,'781#208100000e000100')
        canwait(s,'790:7ff')
        cansend(s,'781#408f000000000000')
        canwait(s,'790:7ff')
        cansend(s,'781#2081000018000100')
        canwait(s,'790:7ff')
        cansend(s,'781#408f000000000000')
        canwait(s,'790:7ff')
        cansend(s,'781#2080000000000000')
        canwait(s,'790:7ff')
        cansend(s,'781#4040000000000000')
        canwait(s,'790:7ff')
        cansend(s,'781#4050000000000000')
        canwait(s,'790:7ff')

#original JSMserial_num = '08901c8a'
JSMserial_num = '08901c8a' # old chair was 08901c8a
#JSMserial_num = '50c01c8f' # new chair


def delta(t):
    print (time()-t)
    return (time())
if __name__ == "__main__":
        global joyx
        global joyy
        
        s = socket.socket(socket.AF_CAN, socket.SOCK_RAW, socket.CAN_RAW)
        s.bind(('can0',))

        cansend(s,'00c#')
        cansend(s,'00e#'+JSMserial_num+'00000000')
        canwait(s,'7b3:7ff')
        cansend(s,'7b2#')
        cansend(s,'7b1#')
        cansend(s,'7b0#')
        cansend(s,'1fb00005#')
        
        canwaitRTR(s,'1f700000:1fff0000') #checks for RTR: 0x1f70XXXX
        cansend(s,'1f0108'+JSMserial_num[0:2]+'#')
        cansend(s,'1f11b1'+JSMserial_num[2:4]+'#')
        cansend(s,'1f211e'+JSMserial_num[4:6]+'#')
        cansend(s,'1f3146'+JSMserial_num[6:8]+'#')
        cansend(s,'1f41dd00#')
        cansend(s,'1f511200#')
        cansend(s,'1f617b00#')
        cansend(s,'1f714500#')
        thread0x00e = canrepeat(s,'00e#'+JSMserial_num+'00000000',50)
        canwait(s,'7b0:7ff') #config level to drop from 7b3 to 7b0
        cansend(s,'7b0#')
        canwait(s,'1c0c0000:1fffffff')
        cansend(s,'1c240101#')
        thread0x3c30f0f = canrepeat(s,'03c30f0f#87878787878787',100)
        #from PM cansend(s,'0c280000#')
        
        canwait(s,'040:7ff')
        cansend(s,'781#2080000011000000')
        canwait(s,'790:7ff')
        cansend(s,'781#4080000000000000')
        canwait(s,'790:7ff')
        
        #                       '   '
        mode='1'
        for bit in range(0,0x20):
            for bitval in {'0','1'}:
                cansend(s,'78'+mode+'#20810000'+dec2hex(bit,2)+'000'+bitval+'00')
                RespToRead = dissect_candump_frame(canwait(s,'790:7f0')).split('#')[1]
                #if RespToRead !='4181000000000000':
                #    print('Read error: ' + RespToRead)
                cansend(s,'78'+mode+'#408F000000000000')
                RespToWrite=dissect_candump_frame(canwait(s,'790:7f0')).split('#')[1]
                if RespToWrite[0]!='C':
                    print('bit '+hex(bit)+' ' + bitval + ' = '+RespToWrite[8:12])
                #else:
                #    print('Err@'+hex(bit)+' ' + bitval + ' '+RespToWrite)
                    
        canrepeat_stop(thread0x3c30f0f)
        canrepeat_stop(thread0x00e)
            
        sys.exit() #------------------------------exit experiment---------------
        
        send_781s_vs2(s)
        cansend(s,'041#00000000') #after 781 / 790 exchanges
        #canwait(s,'040:7ff')
        cansend(s,'041#80000000') #send ack on 040
        canwait(s,'050:7ff')
        cansend(s,'0c180102#0003')
        cansend(s,'061#00400000')
        canwait(s,'060:7ff')
        cansend(s,'0a040100#00') #set power level
        #from PM cansend(s,'0c180000#0101')
        print('JSM Handshake complete')
        joyy = 0x20
        joyx = 0
        start_delay = 0
        joy_id = '02000100'
        jt = threading.Thread(target=send_joystick_canframe,args=(s,joy_id, start_delay,),daemon=True)
        jt.start()
        
        while threading.active_count() > 0:
            r,w,e = select.select([s],[],[])
            if r:
                cf, addr = s.recvfrom(16)
                candump_frame = dissect_candump_frame(cf)
                if candump_frame == '000#R':
                    print('RNET 000#R frame received')
                    break
        
        print("Exiting")
        
        

