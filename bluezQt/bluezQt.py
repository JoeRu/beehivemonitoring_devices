import paho.mqtt.client as mqtt #import the client1
import time
import json
import logging
import urllib.request
import os
import threading
import time
from datetime import datetime

#from influxdb import InfluxDBClient


# influx_client = InfluxDBClient('', 8086, 'openhab', '', 'openhab_db')
# influx_client.switch_database('openhab')

#         ex_payload = json.dumps(values)        
#         influx_client.write_points({
#         "measurement": m_op.name,
#         "tags": {
#             "user":  m_op.name,
#             "topic": message.topic
#         },
#         'time': str(datetime.utcnow()),
#         "fields": values
#         })

#-------------Output Logger
#RUN pip3 install influxdb
# create logger
logger = logging.getLogger("bluezQt")

log_level = {
        'DEBUG' : logging.DEBUG,
        'INFO' : logging.INFO,
        'ERROR' : logging.ERROR
    }
mylog_level = logging.INFO # Default log-level

if 'LOG_LEVEL' in os.environ:
    env_log_level = str(os.environ['LOG_LEVEL'])
    if env_log_level in log_level:
       mylog_level = log_level[env_log_level]
#logger.setLevel(logging.INFO)
logger.setLevel(mylog_level)
# create console handler with a higher log level
ch = logging.StreamHandler()
#ch.setLevel(logging.INFO)
ch.setLevel(mylog_level)
# create formatter and add it to the handlers
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
#formatter = logging.Formatter('%(levelname)s - %(message)s')
ch.setFormatter(formatter)
# add the handlers to the logger
logger.addHandler(ch)
#-------------Output Logger
if 'MQTT_SERVER' in os.environ:
    mqtt_server = os.environ['MQTT_SERVER']
else:
    logger.error("Please set environment-Variable for MQTT_SERVER")
    os.exit()
logger.info("set MQTT_SERVER to {}".format(mqtt_server))

if 'MQTT_PORT' in os.environ:
    mqtt_port = int(os.environ['MQTT_PORT'])
else:
    mqtt_port = 1883
logger.info("set MQTT_PORT to {}".format(mqtt_port))


#######################
#HiveHeart : 04:cd:15:6f:fd:7d
#HiveScale : ec:1b:bd:1c:55:40
# EC1BBD1C5540
#HiveGateway: 7c:d1:c3:34:8f:e2
#
# ec:1b:bd:1c:55:40/0d01c3b8-eff2-44bc-9260-3256eb957268/e11b41bc-6a89-4cf2-828b-9e88b33994c1 
# 19,142,198,37,50,25,26,72
# ec:1b:bd:1c:55:40/0d01c3b8-eff2-44bc-9260-3256eb957268/513849eb-913d-4f80-8c44-3f0685533d6e
# 5,122,89,0,205,197,19,0,128,22,11,70,173,250
class SensorDevice:
    payload = []
    name = ""
    exp_values = {}

    def setpayload(self, pl):
        self.payload = pl

    def Scale(self, value, mul, div): 
        return (value * mul) / div

    def BitField(self, offset, length, signExtend):
        offset += 0x20
        num = offset >> 3
        num2 = ((offset + length) - 1) >> 3
        if ((num > num2) or (num2 >= len(self.payload))):
            return 0
        num3 = 0
        num4 = 0x20 - length
        num5 = num4 - (offset & 7)
        if (num5 < 0):
            num3 |= self.payload[num] >> (- num5)
            num = num + 1
            num5 += 8
        while (num <= num2):        
            num3 |= self.payload[num] << num5
            num = num + 1
            num5 += 8
        if (signExtend):
            return (num3 >> num4)
        return (num3 >> num4)

    def Signed(self, offset, length): 
        return self.BitField(offset, length, True)

    def Unsigned(self, offset, length): 
        return self.BitField(offset, length, False)

    def Voltage(self):
        return round((self.Scale(self.Unsigned(0, 8),2000, 255)+2500)/1000, 4)
        #.Add(0x9c4).ToDecimal(3)
    
    def Pressure(self):
        return (self.Signed(0x1c, 12) + 0x2710)/10      

    def toMQTT(self):
        self.exp_values.clear()
        self.exp_values =  {
            'Pressure': self.Pressure(),
            'Voltage': self.Voltage()
            }
        return self.exp_values

class GatewayDevice(SensorDevice):
    MaxVoltage = 4.05
    MinVoltage = 3.5
    MinRssi = -110
    MaxRssi = -50
    VoltageLimit = 3.6 #M

    def RawVoltage(self):
        self.Unsigned(0, 12)

    def RawPressure(self):
        self.Signed(12, 12)

    def Init(self):
        return self.Unsigned(0x18, 2)

    def SimStatus_Sim(self):
        return self.Unsigned(0x1a, 2)

    def GsmStatus_Gsm(self):
       return self.Unsigned(0x1c, 2)

    def TcpStatus_Tcp(self):
        return self.Unsigned(30, 2)

    def RawMcc(self):
        return self.Unsigned(0x20, 10)

    def RawMnc(self):
        return self.Unsigned(0x2a, 10)

    def RawMnc3Digits(self):
        return self.Unsigned(0x34, 1) == 1

    def RawRssi(self):
        self.Signed(0x38, 8)
    
    def toMQTT(self):
        self.exp_values = super().toMQTT()
        self.exp_values.update({
            'SimStatus_Sim': self.SimStatus_Sim(),
            'GsmStatus_Gsm': self.GsmStatus_Gsm(),
            'TcpStatus_Tcp': self.TcpStatus_Tcp()
            })
        return self.exp_values 


class HiveExternalSensorDevice(SensorDevice):
        def Humidity(self):
            return round(self.Scale(self.Unsigned(8, 8),0x3e8, 0xff),2)/  10

        # hmm nett wirklich
        def Temperature(self):
            return self.Signed(0x10, 12)/10
            #.ToDecimal(1)

        def Weight(self):
            return self.Signed(40, 10)/100

        def RawWeight(self):
            return self.Signed(0x38, 0x18)
       
        def toMQTT(self):
            self.exp_values = super().toMQTT()
            self.exp_values.update({
              'Humidity': self.Humidity(),
              'Temperature' : self.Temperature(),
              'Weight': self.Weight(),
              'RawWeight': self.RawWeight()
            })
            return self.exp_values
 
# Waage = HiveExternalSensorDevice( [
# 208,57,105,0,204,208,17,0,128,222,10,142,197,250
# #    5,122,89,0,205,197,19,0,128,22,11,70,173,250
# #231,20,17,0,120,137,130,112,51,48,0,4,95,170,84,67,33,17,16,0
#     ])

# print("Voltage: " + str(Waage.Voltage()))
# print("Pressure: " + str(Waage.Pressure()))
# print("Humidity: "+ str(Waage.Humidity()))
# print("Temp: " + str(Waage.Temperature()))
# print("Weight: " + str(Waage.Weight()))
# print("-------------------------------------")
# Gateway = GatewayDevice ( [
#     0,194,177,114,53,115,99,104,101,100,117,108,101,114,58,32,83,99,97,110,32,105,110,116,101,114,118,97,108,32,51,54,48,48,44,32,103,111,105,110,103,32,116,111,32,115,108,101,101,112,32,102,111,114,32,51,52,55,50,32,115,101,99,111,110,100,115,46,46,46
# ])

# print("xVoltage: " + str(Gateway.Voltage()))
# print("Gateway Pressure: " + str(Gateway.Pressure()))
# print("SimStatus_Sim: "+ str(Gateway.SimStatus_Sim()))
# print("GsmStatus_Gsm: " + str(Gateway.GsmStatus_Gsm()))
# print("TcpStatus_Tcp: " + str(Gateway.TcpStatus_Tcp()))
###############################################

HiveGateway = GatewayDevice()
HiveGateway.name = "HiveGateway"
HiveScale1 = HiveExternalSensorDevice()
HiveScale1.name = "HiveScale1"
HiveScale2 = HiveExternalSensorDevice()
HiveScale2.name = "HiveScale2"

mqtt_path_op = {
    '84:71:27:cf:10:d3/0d01c3b8-eff2-44bc-9260-3256eb957268/4e78a369-43ec-459f-8678-5bcf8c7cdca2' : HiveGateway, #hivegateway
    'ec:1b:bd:1c:55:40/0d01c3b8-eff2-44bc-9260-3256eb957268/513849eb-913d-4f80-8c44-3f0685533d6e': HiveScale2, #scale 2
    'ec:1b:bd:1c:55:41/0d01c3b8-eff2-44bc-9260-3256eb957268/513849eb-913d-4f80-8c44-3f0685533d6e': HiveScale1 #Scale 1
}
            
logger.info("set mqtt-path to '{}'".format(mqtt_path_op.keys()))


############
def on_message(client, userdata, message):
    spli = str(message.payload.decode("utf-8")).split(',')
    payload = list(map(int, spli))
    logger.debug("1 {}".format(spli))
    logger.debug("2 {}".format(payload))
    
    logger.debug("message received {}".format(message.payload))
    logger.debug("message transformed {}".format(payload))
    logger.debug("message topic= {}".format(message.topic))
    logger.debug("message qos= {}".format(message.qos))
    logger.debug("message retain flag={}".format(message.retain))
    m_op = mqtt_path_op[message.topic] # get class to topic
    logger.debug("M_OP: ={}".format(m_op))
    if isinstance(m_op, SensorDevice):
        m_op.setpayload(payload)
        logger.debug("Name: ={}".format(m_op.name))
        logger.debug("Volate: ={}".format(m_op.Voltage()))
        ex_payload = m_op.toMQTT()
        logger.info("pushing new payload : {}".format(ex_payload))
        client.publish("hive/"+m_op.name, json.dumps(ex_payload), qos=0, retain=True)


########################################
def on_log(client, userdata, level, buf):
    logger.debug("log: {}".format(buf))


logger.debug("creating new instance")
client = mqtt.Client("bluezQt_Client") #create new instance
client.on_message=on_message #attach function to callback
client.on_log=on_log #debug

logger.debug("connecting to broker")
client.connect(mqtt_server, mqtt_port, 60) #connect to broker
for my_topic in mqtt_path_op.keys():
    logger.debug("Subscribing to topic {}".format( my_topic))
    client.subscribe(my_topic)
client.loop_start() #start the loop

exit_thread = False
while not exit_thread:
        # do some work
        time.sleep(3600) # einmal pro Stunde 
        logger.info("restarte MQTT Client....")
        client.disconnect()
        logger.info("connecting to broker")
        client.connect(mqtt_server, mqtt_port, 60) #connect to broker
        for my_topic in mqtt_path_op.keys():
            logger.debug("Subscribing to topic {}".format( my_topic))
            client.subscribe(my_topic)
        client.loop_start() #start the loop

