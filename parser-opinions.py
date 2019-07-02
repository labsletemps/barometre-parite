
# coding: utf-8

# # Baromètre opinions
#
# 1. Séparation interne / externe
# 2. Attribuer genre
# 3. Envoyer résultats à bdd
# 4. Créer graphique en png

import requests
import pandas as pd
import gender_guesser.detector as gender
import datetime
from fuzzywuzzy import fuzz
from math import nan
import re

# config
from define import config

# pour notre log
print(datetime.datetime.now().strftime('%d %B %Y, %H:%M'))

response = requests.get(config['get-opinions'])
df = pd.DataFrame(response.json())

# «opinion» «charivari» ou «édito» en mot-clé ou

df = df[
    (df['chapeau'].str.contains('OPINION|DITORIAL'))
    |
    (df['motcle'].str.contains('charivari|opinion|ditorial', flags=re.IGNORECASE))
].copy()


df['auteur_seul'] = df['auteur'].apply(lambda x: x.split(',')[0])
df['auteur_uni'] = df.apply(lambda row: row['auteur_int'] if row['auteur_int'] != '' else row['auteur_seul'], axis=1)


### df des noms: liste de nos rédacteurs avec leur genre
dfn = pd.read_csv(config['opinions-writer-list'], index_col='Nom')
names_dict = dfn.to_dict()['Genre']

def getRedScore(name):
    if name in names_dict:
        return names_dict[name]
    else:
        for key in names_dict:
            if fuzz.partial_ratio(key, name) >= 80:
                return names_dict[key]
    return nan
df['genre_red'] = df['auteur_uni'].apply(getRedScore)

df['author_is_internal'] = df.apply(lambda row: 1 if (row['auteur_int'] != '' or row['genre_red'] == row['genre_red']) else 0, axis=1)

d = gender.Detector()

def getQuickScore(name):
    name = name.strip()
    if name[:3] in ['Dr ', 'Me ']:
        name = name[3:]

    firstname = name.split()[0]

    # Spacy a tendance à tomber sur des noms de boîtes avec Le / La
    if firstname in ['Le', 'La', 'Les', 'Collectif']:
        return '?'

    # Quelques prénoms manquants
    if firstname in ['Fati', 'Marie-Hélène', 'Aïna', 'Argelia', 'Ngaire']:
        return 'f'
    elif firstname in ['Yelmarc', 'Jean-Blaise', 'Anouch', 'Adrià', 'Pierre-Marcel', 'Wu’er']:
        return 'm'

    result = d.get_gender(firstname)
    males = 0
    females = 0
    unknown = 0

    if result == 'unknown' and firstname.count('-') > 0:
        firstnameNoHyphen = firstname.split('-')[0]
        if firstnameNoHyphen != 'Marie':
            result = d.get_gender(firstnameNoHyphen)

    if result.find('female') >= 0:
        return 'f'
    elif result.find('male') >= 0:
        return 'm'
    else:
        print("Unknown gender:", name)
        return '?'

df['genre'] = df.apply(lambda row: getQuickScore(row['auteur_uni']) if row['genre_red'] != row['genre_red'] else row['genre_red'], axis=1)

df['id'] = df['guid'].apply(lambda x: int(x.split('/')[-1]))

# On retire la revue de presse (plus «news» que opinion) pour ne pas fausser le resultat
df = df[df['motcle'] != 'Revue de presse'].copy()

print('Sans rdp, le df contient maintenant {} lignes.'.format(len(df)))

df['male'] = df['genre'].apply(lambda x: 1 if x == 'm' else 0)
df['female'] = df['genre'].apply(lambda x: 1 if x == 'f' else 0)
df['unknown'] = df['genre'].apply(lambda x: 1 if x == '?' else 0)

def sendJson(_url, _json):
    r = False
    counter = 1
    while counter < 4:
        try:
            r = requests.post(_url, json=_json)
        except requests.exceptions.RequestException as e:
            print ('Attempt', counter, '>', e)
        if r == True:
            if r.status_code == 200:
                print('JSON sent at attempt', counter)
                break
            else:
                print('Attempt', counter, '>', r.status_code)
        counter += 1
    return r

print('Derniere opi: {} {}'.format(df.iloc[0]['titre'], df.iloc[0]['dte_publication']))

payload = {
    'records': df[['id', 'auteur_uni', 'dte_publication', 'titre', 'male', 'female', 'unknown', 'author_is_internal']].to_dict(orient='records'),
}

response = sendJson(config['send-sql-opinions'], payload)

# pour notre log
print(response.text)
print()
