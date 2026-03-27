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
word_block_file.write("TIMESTAMP\tBitLength\t'Dataframe'\n")


with open(file_csv, 'r') as csvfile:
    cvsreader = csv.reader(csvfile, delimiter=',')

    init_state      = next(cvsreader)
    gpio_state      = init_state[GPIO]
    last_timestamp  = float(0)
    last_gpio       = 0
    maxrow          = 20000 #for testing purposes
    outcount        = 0
    distmaxtime     = 50
    prior_word_timestamp = float(0)
    stuffbitone=False
    stuffbitzero=False
    outbinarystring = ''
    heartbeat53HZ = '111101111111001111111110111111111111101111111111111111111111111010010001' #consistant
    heartbeat20HZ  = '1111111100011110111111101110110111111100011011101011111111111111111111111111111111100010101101101101' #consistant
    heartbeat10HZ = '1111000011110000111100001111000011110000111100001111000011110000111100001111000011110000111100010000100110000001' #consistant
    heartbeat4HZ  = '101011110011001111111111111111111111101111111111111111110011101011001001'  #drops out, I suspect this is from the joystick 
    heartbeat1HZ  = '1100111110100011111111111111111111111101111111011101011011110101' #consistant
    heartbeats = [heartbeat53HZ,heartbeat20HZ,heartbeat10HZ,heartbeat4HZ,heartbeat1HZ]
    heartrates = ['53HZ','20HZ','10HZ','4HZ','1HZ']
    
    print "Analysis of "+str(file_len(file_csv))+" csv records proceeding.\n"
    for row in cvsreader:
        if last_gpio != row[GPIO]:
            current_t=float(row[TIMESTAMP])
            delta_t=current_t-last_timestamp
            last_timestamp=current_t
            outtime=int(round(delta_t*1000000))
            #bit_time_file.write(str(outtime)+"\t"+str(1-int(last_gpio))+"\n")
            if outtime>distmaxtime:
                if outbinarystring in heartbeats:
                    i=heartbeats.index(outbinarystring)
                    word_block_file.write( str(row[TIMESTAMP])+"\t"+"\t"*i+"* Beat  "+heartrates[i]+"\n")
                else:
                    #word_block_file.write(str(prior_word_outtime)+"\t"+str( bit_transitions/2)+"\t\t"+outcodestring+"\t\t"+outbinarystring+"\n")
                    word_block_file.write(str(prior_word_timestamp)+"\t"+str(len(outbinarystring))+"\t'"+outbinarystring+"'\n")
                prior_word_timestamp=row[TIMESTAMP] #delay by 1 word
                outbinarystring=''
            if last_gpio == ' 1' and outtime<distmaxtime:
                btime=int((outtime+4)/8)
                if btime==5: stuffbitone=True
                if stuffbitzero:
                    btime -= 1
                    stuffbitzero=False
                outbinarystring += '0'*btime
            if last_gpio == ' 0' and outtime<distmaxtime:
                btime=int((outtime+4)/8)
                if btime==5: stuffbitzero=True
                if stuffbitone:
                    btime -= 1
                    stuffbitone=False
                outbinarystring += '1'*btime
                if btime>5: word_block_file.write('\nbit overrun (noncritical)\n')
                
            outcount += 1
            last_gpio = row[GPIO]
            
        #if outcount > maxrow:
        #    break
    csvfile.close()
    #bit_time_file.close()
    word_block_file.close()  
    print "Analysis files saved.\nExiting.\n"
        
