# wall-it

## Dépendances :

Flask :

```
pip install flask
```

Connexion à Google :

```
pip install httplib2
pip install oauth2client
```

Pygal :

```
pip install pygal
```

Initialisation de la Bdd :

```
sqlite3 /tmp/wallit.db < schema.sql
```

ATTENTION : Si vous voulez ajouter des post-its, vérifiez bien que la personne liée au post-it est dans vos contacts google.
