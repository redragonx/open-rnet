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




file_csv = "chair_data/may17/chair_csv.csv"  #csv file output by Saleae

bit_time_filename = "chair_data/may17/chair_analysis.txt"   #detailed bit time list
bit_time_file = open(bit_time_filename,"w")
bit_time_file.write("microseconds   gpio_state\n")

word_block_filename = "chair_data/may17/chair_word_block.txt"  #data overview including dataword contents
word_block_file = open(word_block_filename,"w")
word_block_file.write("BitTimes legend:\n\tSignal On:  A=8uS B=16uS C=24uS D=32uS ...\n\tSignal Off: 0=8uS 1=16uS 2=24uS 3=32uS ...\n")
word_block_file.write("word_delta_time\t#bits\t\tBitTimes\n")


with open(file_csv, 'r') as csvfile:
    cvsreader = csv.reader(csvfile, delimiter=',')

    # the first entry give us the initial state
    init_state      = next(cvsreader)
    interrupt_state = init_state[TIMESTAMP]
    gpio_state      = init_state[GPIO]
    last_timestamp  = float(0)
    last_gpio       = 0
    maxrow          = 20000 #for testing purposes
    outcount        = 0
    distmaxtime     = 50
    zerodist=array('i',[0]*distmaxtime)
    onedist=array('i',[0]*distmaxtime)
    bit_transitions = 0
    prior_word_outtime =0
    outcodestring = ''
    heartbeatstring = 'D1E1B2E1D1E1E1C1E1E1E1E1E2A2A3A'
    print "Analysis of " + str(file_len(file_csv)) + " csv records proceeding.\n"
    for row in cvsreader:
        if last_gpio != row[GPIO]:
            current_t=float(row[TIMESTAMP])
            delta_t=current_t-last_timestamp
            last_timestamp=current_t
            outtime=int(round(delta_t*1000000))
            bit_time_file.write(str(outtime)+"\t"+str(1-int(last_gpio))+"\n")
            bit_transitions += 1
            if outtime>distmaxtime:
                if outcodestring==heartbeatstring:
                    outcodestring="* beat"
                word_block_file.write(str(prior_word_outtime)+"\t"+str( bit_transitions/2)+"\t\t"+outcodestring+"\n")
                prior_word_outtime=outtime #delay by 1 word
                bit_transitions=0
                outcodestring=''
            if last_gpio == ' 1' and outtime<distmaxtime:
                zerodist[outtime]+=1
                outcodestring +=chr(48+int(outtime/8+.5))
            if last_gpio == ' 0' and outtime<distmaxtime:
                onedist[outtime]+=1
                outcodestring +=chr(64+int(outtime/8+.5))
            outcount += 1
            last_gpio = row[GPIO]

        #if outcount > maxrow:
        #    break
    csvfile.close()
    bit_time_file.close()
    word_block_file.close()
    print "Analysis files saved.\nExiting.\n"
