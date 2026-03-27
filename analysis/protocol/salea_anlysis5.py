import csv
from array import *

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
    return ('0'*hexlen+h)[len(h):len(h)+hexlen]

def Hex2DecSignedByte(val):
    val=int(val,16)
    if val>=128:
        val -= 256
    return val



#file_csv = "/home/that/Desktop/chair_dataMay17/chair_csv.csv"  #csv file output by Saleae
file_csv = "/home/that/Desktop/chair_dataMay24/chair_csvMay24th.csv"  #csv file output by Saleae


""" bit_time files is not being generated at the moment
#bit_time_filename = "/home/that/Desktop/chair_dataMay17/chairMay17_analysis.txt"   #detailed bit time list
bit_time_filename = "/home/that/Desktop/chair_dataMay24/chairMay24_analysis.txt"   #detailed bit time list
bit_time_file = open(bit_time_filename,"w")            
bit_time_file.write("microseconds   gpio_state\n")
"""

#word_block_filename = "/home/that/Desktop/chair_dataMay17/chairMay17_word_block.txt"  #data overview including dataword contents
word_block_filename = "/home/that/Desktop/chair_dataMay24/chairMay24_word_block.txt"  #data overview including dataword contents
word_block_file = open(word_block_filename,"w")           
word_block_file.write("TIMESTAMP\tBitLength\tCANbus decoded\n")


with open(file_csv, 'r') as csvfile:
    cvsreader = csv.reader(csvfile, delimiter=',')

    init_state      = next(cvsreader)
    gpio_state      = init_state[GPIO]
    last_timestamp  = float(0)
    last_gpio       = 0
    maxrow          = 2000000000 #for testing purposes
    outcount        = 0
    distmaxtime     = 50
    prior_word_timestamp = float(0)
    stuffbitone=False
    stuffbitzero=False
    outbinarystring = ''
    heartbeat53HZ = '111101111111001111111110111111111111101111111111111111111111111010010001' #consistant
    heartbeat20HZ = '1111111100011110111111101110110111111100011011101011111111111111111111111111111111100010101101101101' #consistant
    heartbeat10HZ = '1111000011110000111100001111000011110000111100001111000011110000111100001111000011110000111100010000100110000001' #consistant
    heartbeat4HZ  = '101011110011001111111111111111111111101111111111111111110011101011001001'  #drops out, I suspect this is from the joystick 
    heartbeat1HZ  = '1100111110100011111111111111111111111101111111011101011011110101' #consistant
    heartbeats = [heartbeat53HZ,heartbeat20HZ,heartbeat10HZ,heartbeat4HZ,heartbeat1HZ]
    heartrates = ['53HZ','20HZ','10HZ','4HZ','1HZ']
    
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
                if (lbin % 2):   #fudge due to dropped '0' : see stuffbitone
                    outbinarystring+="0"  #changes depending on polarity
                    lbin += 1
                word_block_file.write(str(prior_word_timestamp)+"\t"+str(lbin))
                """                if outbinarystring in heartbeats:
                    i=heartbeats.index(outbinarystring)
                    word_block_file.write( str(row[TIMESTAMP])+"\t"+"  "*i+"* Beat  "+heartrates[i]+"\n")
                """
                if lbin<48:
                    word_block_file.write("\t'"+outbinarystring+"'\n")
                else:
                    
                    IDa = gethex(outbinarystring[1:12],3)
                    srr = outbinarystring[12]
                    ide = outbinarystring[13]
                    IDb = gethex(outbinarystring[14:32],4)
                    rtr = outbinarystring[32]
                    r1r0 = outbinarystring[33:35]
                    dlc=int(outbinarystring[35:39],2)
                    if dlc>0:
                        DAT=gethex(outbinarystring[lbin-17-dlc*8:lbin-17],dlc*2)
                    if IDa=='080' and IDb=='0100' and DAT=='0000':
                        word_block_file.write('\tJoystick IDLE')
                    else:
                        word_block_file.write("\tIDa:"+ IDa)
                        word_block_file.write("\tsrr:"+ srr)
                        word_block_file.write(",ide:"+ ide)
                        word_block_file.write("\tIDb:"+ IDb)
                        word_block_file.write("\trtr:"+ rtr)
                        word_block_file.write(",r1r0:"+ r1r0)
                        word_block_file.write("\tDLC:"+ str(dlc))
                        if dlc>0:                        
                            word_block_file.write("\tDAT:"+ DAT)
                        if IDa=='080' and IDb=='0100':
                            joyx=Hex2DecSignedByte(DAT[0:2])
                            joyy=Hex2DecSignedByte(DAT[2:4])
                            word_block_file.write("\tX="+str(joyx)+"\tY="+str(joyy))
                            
                    word_block_file.write("\n")
                prior_word_timestamp=row[TIMESTAMP] #delay by 1 word
                outbinarystring=''
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
                    
            outcount += 1
            last_gpio = row[GPIO]
            
        if outcount > maxrow:
            break
    csvfile.close()
    #bit_time_file.close()
    word_block_file.close()  
    print "Analysis files saved.\nExiting.\n"

"""
'1 id11101111111 srr0 ide0 idB:111111111011111111 rtr:1 r1r0:11 dlc:1101 data:0110001011111111 crc001001000100011 0 1'	CMD:77f	DLC:2	DAT:62ff
"""

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
        
