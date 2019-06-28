# coding: utf-8

import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
from math import nan

# config
from define import endpoints

# NLP
import spacy
import gender_guesser.detector as gender

# time
import datetime
import time

# to send MQTT message
import paho.mqtt.client as mqtt
import struct

# Get the stories as json

response = requests.get(endpoints['get-stories'])
data = response.json()
df = pd.DataFrame(data)

nlp = spacy.load('fr')
d = gender.Detector()


# countGenders:
# searches for people names with spacy (as nlp)
# count genders with gender.Detector (as d)
# TODO get wikidata gender data?

def countGenders(text):

    people = []
    male_names = []
    female_names = []
    unknown_names = []
    males = 0
    females = 0
    unknown = 0

    doc = BeautifulSoup(text, 'html.parser')
    paragraphs = doc.find_all('p')
    paragraphs = [p.text for p in paragraphs]

#   or everything at once:
#   ptext = "\n".join(paragraphs)
#   sp = nlp(ptext)
    for p in paragraphs:
        sp = nlp(p)

        people.extend('{}'.format(i) for i in sp.ents if i.label_ == 'PER')

    people = [i.strip() for i in people]
    people = [i for i in people if re.search('[A-Z].*[A-Z]', i)]
    people = [i for i in people if not re.search('Monsieur|Madame', i)]
    people = list(set(people))

    for personne in people:
        ## TODO
        # here we could query wikidata
        # and if we get a result, check the “gender” property, P21

        firstname = personne.split()[0]

        # Dirty fix for compound nouns like François-Xavier
        if firstname.count('-') > 0:
            if firstname.split('-')[0] == 'Marie': # In this case, we use the last first name
                firstname = firstname.split('-')[-1]
            else:
                firstname = firstname.split('-')[0]

        result = d.get_gender(firstname)

        if result.find('female') >= 0:
            female_names.append(personne)
            females += 1
        elif result.find('male') >= 0:
            male_names.append(personne)
            males += 1
        else:
            unknown_names.append(personne)
            unknown += 1

    return {'male': males, 'female': females, 'total': males + females, 'unknown': unknown, 'male_names': male_names, 'female_names': female_names, 'unknown_names': unknown_names}

df['score'] = df['contenu'].apply(countGenders)

def computeRatio(counts):
    if counts['total'] > 0:
        return counts['female'] / counts['total']
    else:
        return nan
df['ratio'] = df['score'].apply(computeRatio)

df['percentage'] = df['ratio'].apply(lambda x: "{0:.2f}%".format(x*100) if x == x else 'n/a')

mean = df['ratio'].mean() * 100

################
# MQTT
#

client = mqtt.Client("xoxox")
client.connect(endpoints['mqtt-broker'], port=1883)

# change the ratio (from inMin to inMax) to an angle (from outMin to outMax)
def remap( x, inMin, inMax, outMin, outMax ):
    portion = (x-inMin)*(outMax-outMin)/(inMax-inMin)
    result = portion + outMin # add the new minimal value
    return int(round(result))

# let’s remap the ratio, from percentange to servomotor angle
remapped = remap(mean, 0, 100, 12, 181)

print('Mean: {}, angle: {}'.format(mean, remapped))
x = struct.pack('i', remapped)

response = client.publish(endpoints['mqtt-topic'], x, qos=0, retain=True)
print("MQTT message published:", response.is_published())

ts = datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ')
data = {'mean': mean, 'update': ts}

print(data)

################
# Send data to SQLITE database
#

df['male'] = df['score'].apply(lambda x: x['male'])
df['female'] = df['score'].apply(lambda x: x['female'])
df['unknown'] = df['score'].apply(lambda x: x['unknown'])
df['id'] = df['guid'].apply(lambda x: int(x.split('/')[-1]))
df['auteur_seul'] = df['auteur'].apply(lambda x: x.split(',')[0])
df['auteur_uni'] = df.apply(lambda row: row['auteur_int'] if row['auteur_int'] != '' else row['auteur_seul'], axis=1)

df['male_names'] = df['score'].apply(lambda x: ", ".join(x['male_names']))
df['female_names'] = df['score'].apply(lambda x: ", ".join(x['female_names']))
df['unknown_names'] = df['score'].apply(lambda x: ", ".join(x['unknown_names']))
df['ratio'] = df['ratio'].apply(lambda x: 'NULL' if x != x else x)

def sendJson(_url, _json):
    r = False
    counter = 1
    while counter < 4:
        try:
            r = requests.post(_url, json=_json)
        except requests.exceptions.RequestException as e:  # This is the correct syntax
            print ('Attempt', counter, '>', e)
        if r == True:
            if r.status_code == 200:
                print('JSON sent at attempt', counter)
                break
            else:
                print('Attempt', counter, '>', r.status_code)
        counter += 1
    return r

payload = {
    'records': df[['id', 'section', 'auteur_uni', 'dte_publication', 'titre',
                   'male', 'female', 'unknown',
                   'male_names', 'female_names', 'unknown_names',
                   'ratio']].to_dict(orient='records'),
}

response = sendJson(endpoints['send-sql-stories'], payload)

print('Resultat SQLite:', response.text)

print('End')
