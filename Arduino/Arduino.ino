#define sygPrzek 8
#define sygWiatr 6
#define sygZwrt 7

#include <SPI.h>
#include <Ethernet.h>
#include <EthernetClient.h>
#include <ArduinoJson.h>
#include <HttpClient.h>

const char kHostname[] ="192.168.1.17";
const char kHostname2[] ="192.168.1.17";
const char kPath[] = "/kompresor/2";
const char kPath2[] = "/kompresor/2";

byte mac[] = { 0xDE, 0xAD, 0xBE, 0xEF, 0xFE, 0xED };
byte ip[] = { 192, 168, 1, 69 };  

unsigned long time_current = 0;
unsigned long time_difference = 0;

struct URZADZENIE{
  boolean stan; 
  int predkosc;
};

URZADZENIE wentylator;

void Oczekiwanie(int period)
{
  time_current = millis();        
  time_difference = millis() - time_current;
  while (period > time_difference)
  {
    time_difference = millis() - time_current;
  }
}

EthernetClient client;

void setup() 
{
  pinMode(sygPrzek, OUTPUT);
  pinMode(sygWiatr, OUTPUT);
  pinMode(sygZwrt, INPUT);

  digitalWrite(sygPrzek, HIGH);
  analogWrite(sygWiatr, 0);
  
  Serial.begin(9600);
  while (!Serial) 
  {
    ; // wait for serial port to connect. Needed for native USB port only
  }
  //Serial.println("Nawiązano komunikację poprzez port szeregowy!");
  Ethernet.begin(mac, ip);
  if (Ethernet.hardwareStatus() == EthernetNoHardware) 
  {
    //Serial.println("Nie wykryto nakładki Ethernet. Nie można rozpocząć bez sprzętu. :(");

    while (true) 
    {
      Oczekiwanie(1); // do nothing, no point running without Ethernet hardware
    }
  }
  else
  {
    //Serial.println("Wykryto nakładkę Ethernet.");
    
    //Serial.println("Poprawnie zainicjalizowano bibliotekę oraz ustawienia sieci. Adres IP Arduino: ");
    //Serial.println(Ethernet.localIP());  
  }
  //Serial.println("Inicjalizacja przebiegła pomyślnie!");
  Oczekiwanie(1000);
}

void loop() 
{
  obslugaKompresora();
  Oczekiwanie(1000);   
}

void postDataToServer(bool stan)
{
  if(connect(kHostname, 5000))
  {
    if(sendRequest(kHostname, kPath2, stan) && skipResponseHeaders())
    {
      //Serial.println("Żądanie POST zakończone");
    }
  }
  disconnect();
}

bool connect(const char* kHostname, int portNumber)
{
  //Serial.println("Próba połączenia z: ");
  //Serial.println(kHostname);
  bool ok = client.connect(kHostname, portNumber);
  //Serial.println(ok ? "Połączono!" : "Połączenie nieudane!");
  return ok;
}

bool sendRequest(const char* kHostname, const char* kPath, bool stan)
{
  StaticJsonBuffer<40> jsonBuffer;
  JsonObject& root = jsonBuffer.createObject();
  
  root["is_power_on"] = stan;
  
  root.printTo(Serial);

  //Serial.print("PUT ");
  //Serial.println(kPath);

  client.print("PUT ");
  client.print(kPath);
  client.println(" HTTP/1.1");
  client.print("Host: ");
  client.println(kHostname);
  client.println("Connection: close\r\nContent-Type: application/json");
  client.print("Content-Length: ");
  client.print(root.measureLength());
  client.print("\r\n");
  client.println();
  root.printTo(client);

  return true;
}

bool skipResponseHeaders()
{
  char endOfHeaders[] = "\r\n\r\n";

  client.setTimeout(30000);
  bool ok = client.find(endOfHeaders);

  if(!ok)
  {
    //Serial.println("Brak odpowiedzi lub odpowiedź nieprawidłowa");
  }
  return ok;
}

void disconnect()
{
  //Serial.println("Rozłączono");
  client.stop();
}

void getDataFromServer()
{
  String response = "";
  
  int err = 0;

  HttpClient  http(client);

  err = http.get(kHostname2,5000, kPath);
  if(err == 0)
  {
    //Serial.println("Poprawnie rozpoczęto żądanie");
    err = http.responseStatusCode();
    if(err >= 0)
    {
      //Serial.println("Otrzymano kod: ");
      //Serial.println(err);
      err = http.skipResponseHeaders();
      if(err>=0)
      {
        int bodyLen = http.contentLength();
        //Serial.println("Rozmiar zawartości: ");
        //Serial.println(bodyLen);
        //Serial.println();
        Serial.println("Body zwróciło: ");

        unsigned long timeoutStart = millis();
        char c;

        while ((http.connected() || http.available()) && ((millis() - timeoutStart) < 30000))
        {
          if (http.available())
          {
            c = http.read();
            response = response + (String)c;
            //Serial.print(c);
            bodyLen--;
            timeoutStart = millis();
          }
          else
          {
            Oczekiwanie(1000);
          }
        }
        Serial.println(response);
        StaticJsonBuffer<90> jsonBuffer;
        JsonArray& root = jsonBuffer.parseArray(response);
        if(root.success())
        {
          //Serial.println("Udało się sparsować jsona!");
        }
        JsonObject& wynik = root[0];
        wentylator.stan = wynik["power_on"];
        wentylator.predkosc = wynik["value"];
      }
      else
      {
        //Serial.println("Nie udało się pominąć nagłówków: ");
        //Serial.println(err);
      }
    }
    else
    {
      //Serial.println("Nie udało się uzyskać odpowiedzi: ");
      //Serial.println(err);
    }
  }
  else
  {
    //Serial.println("Nie udało się połączyć: ");
    //Serial.println(err);
  }
  http.stop();
}

void obslugaKompresora()
{
  getDataFromServer();
  
  if(wentylator.stan == true)
  {
    //Serial.println("Załączam wentylator!");
    digitalWrite(sygPrzek, LOW);
    Oczekiwanie(150);
    analogWrite(sygWiatr, wentylator.predkosc);
  }
  if(wentylator.stan == false)
  {
    //Serial.println("Wyłączam wentylator!");
    analogWrite(sygWiatr, 0);
    Oczekiwanie(150);
    digitalWrite(sygPrzek, HIGH);
  }
  if(digitalRead(sygZwrt) == HIGH)
  {
    postDataToServer(true);
  }
  else
  {
    postDataToServer(false);
  }
}