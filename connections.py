import ubluetooth
import network
from machine import Pin
from machine import Timer
from time import sleep

class WiFiManager:
    wifi = network.WLAN(network.STA_IF)
    @staticmethod
    def getList() -> list:
      WiFiManager.wifi.active(True)
      scan_results = WiFiManager.wifi.scan()
      
      wifi_list = []
      for result in scan_results:
          ssid = result[0].decode("utf-8")
          rssi = result[3]
          encrypted = "Open" if result[4] == 0 else "Password"
          
          wifi_info = {
              "ssid": ssid,
              "rssi": rssi,
              "encrypted": encrypted
          }
          wifi_list.append(wifi_info)
      
      return wifi_list
    
    @staticmethod
    def connect(ssid: str, password: str) -> bool:       
        if not WiFiManager.wifi.isconnected():
            WiFiManager.wifi.active(True)
            WiFiManager.wifi.connect(ssid, password)
            print("connecting in wifi: "+ssid)
            print("connect", end="")
            for _ in range(20):
                if WiFiManager.wifi.isconnected():
                    return True
                print(".", end="")
                sleep(1)
        return False
    
    @staticmethod
    def disconnect() -> None:
        WiFiManager.wifi.disconnect()
        WiFiManager.wifi.active(False)
        print("disconnecting wifi")
class BluetoothManager():
    def __init__(self, name):
        self.__led = Pin(13, Pin.OUT)
        self.__timer1 = Timer(0)
        self.__ble_msg = ""
        
        self.__name = name
        self.__ble = ubluetooth.BLE()
        self.__ble.active(True)
        self.__disconnected()
        self.__ble.irq(self.__ble_irq)
        self.__register()
        self.__advertiser()

    def __connected(self):
        self.__led.value(0)
        self.__timer1.deinit()

    def __disconnected(self):        
        self.__timer1.init(period=100, mode=Timer.PERIODIC, callback=lambda t: self.__led.value(3))

    def __ble_irq(self, event, _data):      
        if event == 1: #_IRQ_CENTRAL_CONNECT:
                       # A central has connected to this peripheral
            self.__connected()

        elif event == 2: #_IRQ_CENTRAL_DISCONNECT:
                         # A central has disconnected from this peripheral.
            self.__disconnected()
            self.__advertiser()
        
        elif event == 3: #_IRQ_GATTS_WRITE:
                         # A client has written to this characteristic or descriptor.          
            buffer = self.__ble.gatts_read(self.__rx)
            self.__ble_msg = buffer.decode('UTF-8').strip()
            
    def __register(self):        
        # Nordic UART Service (NUS)
        NUS_UUID = '6E400001-B5A3-F393-E0A9-E50E24DCCA9E'
        RX_UUID = '6E400002-B5A3-F393-E0A9-E50E24DCCA9E'
        TX_UUID = '6E400003-B5A3-F393-E0A9-E50E24DCCA9E'
            
        BLE_NUS = ubluetooth.UUID(NUS_UUID)
        BLE_RX = (ubluetooth.UUID(RX_UUID), ubluetooth.FLAG_WRITE)
        BLE_TX = (ubluetooth.UUID(TX_UUID), ubluetooth.FLAG_NOTIFY)
            
        BLE_UART = (BLE_NUS, (BLE_TX, BLE_RX,))
        SERVICES = (BLE_UART, )
        ((self.__tx, self.__rx,), ) = self.__ble.gatts_register_services(SERVICES)

    def send(self, data: str, end="\n") -> None:
        self.__ble.gatts_notify(0, self.__tx, data + end)

    def write(self) -> str:
        msg = self.__ble_msg
        while msg == "": msg = self.__ble_msg
        self.__ble_msg = ""
        return msg

    def __advertiser(self):
        name = bytes(self.__name, 'UTF-8')
        adv_data = bytearray(b'\x02\x01\x02') + bytearray((len(name) + 1, 0x09)) + name
        self.__ble.gap_advertise(100, adv_data)