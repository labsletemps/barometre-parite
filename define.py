from dotenv import load_dotenv
import os
load_dotenv()

config = {
    'get-stories': os.getenv('GET-STORIES'),
    'send-sql-stories': os.getenv('SEND-SQL-STORIES'),
    'mqtt-broker': os.getenv('MQTT-BROKER'),
    'mqtt-topic': os.getenv('MQTT-TOPIC'),
    'get-opinions': os.getenv('GET-OPINIONS'),
}
