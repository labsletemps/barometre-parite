# Baromètre de la parité en temps réel

### Mentions dans les articles
**scraper.py**: repère les noms propres grâce à Spacy, leur attribue un genre.

Développement possible: utiliser Wikidata pour obtenir le genre des personnalités.

### Auteurs d’opinions
**scraper-opinions.py**: compte le genre des auteurs d’opinions écrites par la rédaction (éditoriaux, chroniques)et par des contributeurs externes (pages débats).

### Base de données sqlite

**(sqlite)[sqlite]** crée deux tables, une pour les mentions dans les articles, une autre pour les signatures d’opinions.

### Config

Editer le fichier **.dist.env** et le renommer .env
