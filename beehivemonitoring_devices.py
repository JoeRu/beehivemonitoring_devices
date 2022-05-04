
#######################
# example data procured by a https://docs.openmqttgateway.com/ BLE device.
#HiveHeart : 04:cd:15:6f:fd:7d # mac-adress
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
        self.exp_values.update( {
            'Pressure': self.Pressure(),
            'Voltage': self.Voltage()
            })
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
            'TcpStatus_Tcp': self.TcpStatus_Tcp(),
            'RawRssi': self.RawRssi()
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


 
Waage = HiveExternalSensorDevice()
Waage.setpayload( [
208,57,105,0,204,208,17,0,128,222,10,142,197,250
#    5,122,89,0,205,197,19,0,128,22,11,70,173,250
#231,20,17,0,120,137,130,112,51,48,0,4,95,170,84,67,33,17,16,0
    ])

print("Voltage: " + str(Waage.Voltage()))
print("Pressure: " + str(Waage.Pressure()))
print("Humidity: "+ str(Waage.Humidity()))
print("Temp: " + str(Waage.Temperature()))
print("Weight: " + str(Waage.Weight()))
print(Waage.toMQTT())
print("-------------------------------------")
Gateway = GatewayDevice ( )
Gateway.setpayload([
    0,194,177,114,53,115,99,104,101,100,117,108,101,114,58,32,83,99,97,110,32,105,110,116,101,114,118,97,108,32,51,54,48,48,44,32,103,111,105,110,103,32,116,111,32,115,108,101,101,112,32,102,111,114,32,51,52,55,50,32,115,101,99,111,110,100,115,46,46,46
])
print("xVoltage: " + str(Gateway.Voltage()))
print("Gateway Pressure: " + str(Gateway.Pressure()))
print("SimStatus_Sim: "+ str(Gateway.SimStatus_Sim()))
print("GsmStatus_Gsm: " + str(Gateway.GsmStatus_Gsm()))
print("TcpStatus_Tcp: " + str(Gateway.TcpStatus_Tcp()))