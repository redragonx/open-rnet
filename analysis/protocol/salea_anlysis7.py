import csv
from array import *
from time import *

TIMESTAMP  = 0
GPIO       = 1

def file_len(fname):
    with open(fname) as f:
        for i, l in enumerate(f):
            pass
    f.close()
    return i + 1

def gethex(bits,hexlen):  #convert binary to hex with leading 0s and no '0x' 
    h=hex(int(bits,2))[2:]
    l=len(h)
    if h[l-1]=="L":
        l-=1  #strip of 'L' that python int stick on
    return ('0'*hexlen+h)[l:l+hexlen]

def Hex2DecSignedByte(val):
    val=int(val,16)
    if val>=128:
        val -= 256
    return val

def fprint(s):
    word_block_file.write(s)

def getLittleEndian16(s):
    i = int(s[2:4]+s[0:2],16)
    return i

def getLittleEndian32(s):
    i = int(s[6:8]+s[4:6]+s[2:4]+s[0:2],16)
    return i

#file_csv = "/home/that/Desktop/chair_dataMay17/chair_csv.csv"  #csv file output by Saleae
file_csv = "/home/that/Desktop/chair_dataMay24/chair_csvMay24th.csv"  #csv file output by Saleae


""" bit_time files is not being generated at the moment
#bit_time_filename = "/home/that/Desktop/chair_dataMay17/chairMay17_analysis.txt"   #detailed bit time list
bit_time_filename = "/home/that/Desktop/chair_dataMay24/chairMay24_analysis.txt"   #detailed bit time list
bit_time_file = open(bit_time_filename,"w")            
bit_time_file.write("microseconds   gpio_state\n")
"""

start_time=time()

#word_block_filename = "/home/that/Desktop/chair_dataMay17/chairMay17_word_block.txt"  #data overview including dataword contents
word_block_filename = "/home/that/Desktop/chair_dataMay24/chairMay24_word_block.txt"  #data overview including dataword contents
word_block_file = open(word_block_filename,"w")           
word_block_file.write("TIMESTAMP\tBitLength\tCANbus decoded\tALL commands are a best guess.  Keep that in mind.\n")


with open(file_csv, 'r') as csvfile:
    cvsreader = csv.reader(csvfile, delimiter=',')
    init_state      = next(cvsreader)
    gpio_state      = init_state[GPIO]
    last_timestamp  = float(0)
    last_gpio       = 0
#    maxrow          = 2000 #for testing purposes
    maxrow          = 100000 #for testing purposes
    outcount        = 0
    distmaxtime     = 50
    prior_word_timestamp = float(0)
    stuffbitone=False
    stuffbitzero=False
    outbinarystring = ''

    #print "Analysis of "+str(file_len(file_csv))+" csv records "
    print "proceeding.\n"
    for row in cvsreader:
        if last_gpio != row[GPIO]:
            current_t=float(row[TIMESTAMP])
            delta_t=current_t-last_timestamp
            last_timestamp=current_t
            outtime=int(round(delta_t*1000000))
            if outtime>=distmaxtime:
                lbin=len(outbinarystring)
                if (lbin % 2):   #fudge due to dropped bit at end of frame due to stuffbit removal
                    if outbinarystring[lbin-1]=="1":
                        outbinarystring+="0"
                    else:
                        outbinarystring+="1"
                    lbin += 1
                fprint(str(prior_word_timestamp)+"\t"+str(lbin))
                if lbin<48:
                    word_block_file.write("\t'"+outbinarystring+"'\n")
                else:
                    IDa = gethex(outbinarystring[1:12],3)
                    srr = outbinarystring[12]
                    ide = outbinarystring[13]
                    IDb = gethex(outbinarystring[14:32],5)
                    rtr = outbinarystring[32]
                    r1r0 = outbinarystring[33:35]
                    dlc=int(outbinarystring[35:39],2)
                    if dlc>0:
                            DAT=gethex(outbinarystring[lbin-17-dlc*8:lbin-17],dlc*2)
                    ID=IDa+IDb #"X"
                    fprint("\tID:" + ID + "\t'"+srr+ide+rtr+r1r0+"'\t")
                    if ID=='28100100':
                        fprint("SETSPEED\t" + str(int(DAT[0:2],16))+"%")
                    elif ID=='30000005': fprint("M-BREAK\toff")
                    elif ID=='30000006': fprint("M-BREAK\tON")
                    elif ID=='30100100': fprint("HORN\tON!")
                    elif ID=='30100101': fprint("HORN\toff")
                    elif ID=='70900101': fprint(".05HZ")
                    elif ID=='30500000': fprint("1HZ\tDAT:"+DAT)
                    elif ID=='0f030f0f': fprint("10HZ\tDAT:"+DAT)
                    elif ID=='00e10112': fprint("20HZ\tDAT:"+DAT)
                    #elif ID=='00e10112': fprint("\t"+outbinarystring)
                    elif ID=='30600000': fprint("MODEinterlinkA\tDAT:"+DAT)
                    elif ID=='30600001': fprint("MODEinterlinkB\tDAT:"+DAT)
                    elif ID=='30600102': fprint("MODEinterlinkC\tDAT:"+DAT)
                    elif ID=='06108008' and r1r0=='00': fprint("LIFTMODE\tREQUEST")
                    elif ID=='06108008' and r1r0=='01': fprint("LIFTMODE\tREPLY")
                    elif ID=='06108808' and r1r0=='00': fprint("DRIVEMODE\tREQUEST")
                    elif ID=='06108808' and r1r0=='01': fprint("DRIVEMODE\tREPLY")
                    elif ID=='70c00004':
                        fprint('BATTERYLVL?\ta=' + \
                        str(getLittleEndian32(DAT[0:8])) + \
                        '\tb='+str(getLittleEndian32(DAT[8:16])))
                    
                    elif ID=='60700100':
                        fprint("REFRESH-UI\tDAT:"+DAT)
                    elif ID=='70300000':
                        fprint("1HZ [46->5A]\tDAT:"+DAT)
                    elif ID=='06009200':
                        fprint(".2HZ ?MODE?\tr0:"+r1r0[1])
                    elif ID=='08000100':
                        if DAT=='0000': fprint("JOYSTICK\tidle")
                        else:
                            joyx=Hex2DecSignedByte(DAT[0:2])
                            joyy=Hex2DecSignedByte(DAT[2:4])
                            fprint("JOYSTICK\tX="+str(joyx)+"\tY="+str(joyy))
                    elif ID=='50c00000':
                        fprint("M-POWERDRAW\t" + \
                        str(getLittleEndian16(DAT)))
                    else:
                        word_block_file.write("\tsrr:"+ srr)
                        word_block_file.write(",ide:"+ ide)
                        #word_block_file.write("\tIDb:"+ IDb)
                        word_block_file.write("\trtr:"+ rtr)
                        word_block_file.write(",r1r0:"+ r1r0)
                        word_block_file.write("\tDLC:"+ str(dlc))
                        if dlc>0:
                            if dlc <= 8:
                                word_block_file.write("\tDAT:"+ DAT)
                            else:
                                word_block_file.write("\tDAT:?>8?")
                    word_block_file.write("\n")
                prior_word_timestamp=row[TIMESTAMP] #delay by 1 word
                outbinarystring=''
                outcount += 1
                if outcount > maxrow:
                    break
            else:
                if last_gpio == ' 0':
                    btime=int((outtime+4)/8)
                    if btime==5: stuffbitone=True
                    if stuffbitzero:
                        btime -= 1
                        stuffbitzero=False
                    outbinarystring += '0'*btime
                    if btime>5:
                        word_block_file.write("CANbus ERROR FRAME\n")
                if last_gpio == ' 1':
                    btime=int((outtime+4)/8)
                    if btime==5: stuffbitzero=True
                    if stuffbitone:
                        btime -= 1
                        stuffbitone=False
                    outbinarystring += '1'*btime
                    if btime>5: word_block_file.write('\nbit overrun (noncritical)\n')
            last_gpio = row[GPIO]
    csvfile.close()
    word_block_file.close()  
    print str(outcount)+" frames processed.\n"
    print "Elapsed "+str(int(time()-start_time))+" seconds.\n"
    print "Analysis files saved.\nExiting.\n"

"""
C code for CAN bus CRC calcs ripped from http://blog.qartis.com/can-bus/
#include <stdio.h>
#include <stdint.h>

uint16_t can_crc_next(uint16_t crc, uint8_t data)
{
    uint8_t i, j;

    crc ^= (uint16_t)data << 7;

    for (i = 0; i < 8; i++) {
        crc <<= 1;
        if (crc & 0x8000) {
            crc ^= 0xc599;
        }
    }

    return crc & 0x7fff;
}

int main()
{
    int i;
    uint8_t data[] = {0x02, 0xAA, 0x80};
    uint16_t crc;

    crc = 0;

    for (i = 0; i < sizeof(data); i++) {
        crc = can_crc_next(crc, data[i]);
    }

    printf("%x\n", crc);
}
"""
        
