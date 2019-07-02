/*
 * Code pour puce ESP8266
 * - Connexion à un réseau Wi-Fi domestique
 * - LED stable: pas de problème, clignotante: en attente, SOS: aïe
 * - deep sleep pour économiser l'énergie
 *
 */

#include <ESP8266WiFi.h>
#include <PubSubClient.h>
#include <Servo.h>
#include <Task.h>

extern "C" {
  #include "user_interface.h"
}

#define DEFAULT_SLEEPING_TIME 28 * 1000000

TaskManager taskManager;
struct SleepState {
  uint8_t persistentCount;
  uint8_t persistentServoPosition;
};

SleepState state;

// nos codes pour le wi-fi

const char* ssid = "YOUR-SSID";
const char* password = "YOUR-PASSWORD";

// backup wi-fi
const char* ssidb = "YOUR-BACKUP-SSID";
const char* passwordb = "YOUR-BACKUP-PASSWORD";

// notre broker MQTT
const char* mqtt_server = "YOUR-BROKER";

// LED externe et servomoteur
int ledPin = 13;
Servo myservo;

// wifi
WiFiClient espClient;
PubSubClient client(espClient);

// on compte les tentatives pour eviter un blocage dans une boucle
int WiFiattempts = 0;
int MQTTattempts = 0;
int suscriptionAttempts = 0;

void lightenLED(float seconds){
  digitalWrite(ledPin, HIGH);
  delay(500 * seconds);
  digitalWrite(ledPin, LOW);
  delay(250);
}

void sendSOS() {
    digitalWrite(ledPin, LOW);
    delay(250);
    digitalWrite(ledPin, HIGH);
    delay(500);
    digitalWrite(ledPin, LOW);
    delay(250);
    digitalWrite(ledPin, HIGH);
    delay(1000);
    digitalWrite(ledPin, LOW);
    delay(250);
    digitalWrite(ledPin, HIGH);
    delay(500);

    digitalWrite(ledPin, LOW);
    delay(250);
    digitalWrite(ledPin, HIGH);
    delay(500);
    digitalWrite(ledPin, LOW);
    delay(250);
    digitalWrite(ledPin, HIGH);
    delay(1000);
    digitalWrite(ledPin, LOW);
    delay(250);
    digitalWrite(ledPin, HIGH);
    delay(500);
}

void setup_wifi() {
  digitalWrite(ledPin, HIGH);
  delay(100);

  Serial.print("On se connecte a ");
  Serial.println(ssid);
  WiFi.begin(ssid, password);

  while (WiFi.status() != WL_CONNECTED)
  {
    digitalWrite(ledPin, LOW);
    delay(250);
    digitalWrite(ledPin, HIGH);
    delay(250);
    Serial.print(".");
    WiFiattempts += 1;
    if( WiFiattempts == 45 ){
      sendSOS();
      Serial.println("backup wifi");
      WiFi.begin(ssidb, passwordb);
    }
    if( WiFiattempts > 60 ){
      sendSOS();
      taskManager.EnterSleep(DEFAULT_SLEEPING_TIME, &state, sizeof(state));
    }
  }
  randomSeed(micros());
  Serial.println("");
  Serial.println("Connexion WiFi etablie");
  Serial.println("Addresse IP: ");
  Serial.println(WiFi.localIP());
}

// s'execute quand on recoit une commande
void callback(char* topic, byte* payload, unsigned int length)
{
  Serial.print("Commande du broker: ");
  digitalWrite(ledPin, LOW);
  int targetPos;

  for(int i=0;i<length;i++)
  {
    // Serial.println(payload[i]);
    if((int)payload[i]>194||(int)payload[i]<0)
    break;

    Serial.print((int)payload[i]);
    Serial.println();


    // On bouge le servo progressivement
    // en utilisant d'abord servo.read()
    int currentPos = myservo.read();
    targetPos = (int)payload[i];
    int pos;

    Serial.print("Current pos = ");
    Serial.print((int) currentPos);
    Serial.println();

    if (currentPos == targetPos){
      Serial.println("Same pos.");
    } else if (currentPos < (int)payload[i]) {
      for (pos = currentPos; pos <= targetPos; pos += 1) {
        myservo.write(pos);
        Serial.println((int) pos);
        delay(150);
      }
    } else {
      for (pos = currentPos; pos >= targetPos; pos -= 1) {
        myservo.write(pos);
        Serial.println((int) pos);
        delay(150);
      }
    }

    break;
  }

  digitalWrite(ledPin, HIGH);
  delay(250);
  digitalWrite(ledPin, LOW);
  delay(250);
  digitalWrite(ledPin, HIGH);

  Serial.println("Execution correcte, retour compteur a zero");
  state.persistentCount = 0;
  state.persistentServoPosition = targetPos;

  // on dort
  Serial.println("Je pars en deep sommeil");
  taskManager.EnterSleep(DEFAULT_SLEEPING_TIME, &state, sizeof(state));

}//end callback

void reconnect() {
  // Loop until we're reconnected
  while (!client.connected())
  {
    Serial.print("Connection MQTT...");
    // ID random
    String clientId = "YOUR-TOPIC";
    clientId += String(random(0xffff), HEX);

    // On tente la connexion
    // NB Ajout mdp?
    //   if (client.connect(clientId.c_str(), "bieg-client", "r4reLo0phOle")) {

    if (client.connect(clientId.c_str()))
    {
      Serial.println("Connexion faite");

      // Souscription à la commande
      client.subscribe("YOUR-TOPIC");
    } else {
      Serial.print("failed, rc=");
      Serial.print(client.state());
      Serial.println("nouvel essai dans 5 sec");
      suscriptionAttempts += 1;

      // On s'arrete apres deux essais (ca repartira de zero)
      if(suscriptionAttempts > 2){
        Serial.println("Deep sleep apres deux suscriptionAttempts ratees");
        taskManager.EnterSleep(DEFAULT_SLEEPING_TIME, &state, sizeof(state)); // (25e6); // dodo 25 secondes
      }

      delay(5000);
    }
  }
} //end reconnect()

void setup() {
  Serial.begin(115200);

  if (!taskManager.RestartedFromSleep(static_cast<void*>(&state), sizeof(state))) {
    // Premier démarrage
    Serial.println("Je dormais pas");
    state.persistentCount = 120;

    // si pas encore de valeur stockee en memoire
    if((state.persistentServoPosition < 10) || (state.persistentServoPosition > 180)){
      state.persistentServoPosition = 50;
    }
  }

  pinMode(ledPin, OUTPUT);

  myservo.write(state.persistentServoPosition);
  myservo.attach(2);  // NodeMCU: GIO2 = D4

  Serial.println("");
  Serial.print("Decompte en memoire: ");
  Serial.println(state.persistentCount);

  Serial.print("Position servo en memoire: ");
  Serial.println(state.persistentServoPosition);

  // 1 declenchement par heure
  // 1h = 3600 secondes
  // lancer au 120e declenchement
  if(state.persistentCount < 2){
    Serial.println("Moins de 120 -> stand by");
    state.persistentCount++;
    delay(2000); // pour flasher plus facilement - sinon deconnecter les pins RST et D0

    taskManager.EnterSleep(DEFAULT_SLEEPING_TIME, &state, sizeof(state)); // 60 seconds

  }else{
    setup_wifi();
    client.setServer(mqtt_server, 1883);
    client.setCallback(callback);
  }
}

void loop() {
  if (!client.connected()) {
    MQTTattempts += 1;
    if (MQTTattempts > 5) {
      // on arrete la boucle: deep sleep
      Serial.println("Deep sleep apres cinq MQTTattempts");
      taskManager.EnterSleep(DEFAULT_SLEEPING_TIME, &state, sizeof(state)); // (25e6); // 60e6
    }
    reconnect();
  }
  client.loop();

}
